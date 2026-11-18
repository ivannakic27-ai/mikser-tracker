import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

typedef Json = Map<String, dynamic>;

double? num_(dynamic x) => x == null ? null : (x as num).toDouble();

String eur(double? v) => v == null ? '?' : '${v.toStringAsFixed(2).replaceAll('.', ',')} €';

String ago(String? iso) {
  if (iso == null) return 'nepoznato';
  final t = DateTime.tryParse(iso)?.toLocal();
  if (t == null) return 'nepoznato';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 2) return 'upravo';
  if (d.inHours < 1) return 'prije ${d.inMinutes} min';
  if (d.inDays < 1) return 'prije ${d.inHours} h';
  return 'prije ${d.inDays} d';
}

String stripHtml(String s) => s
    .replaceAll(RegExp(r'<[^>]*>'), '')
    .replaceAll('&amp;', '&')
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>');

/// Supabase access + offline cache (last successful response is kept in SharedPreferences).
class Repo {
  static final Repo i = Repo._();
  Repo._();
  SupabaseClient get _c => Supabase.instance.client;
  bool offline = false;

  Future<List<Json>> _get(String key, Future<List<dynamic>> Function() q) async {
    final p = await SharedPreferences.getInstance();
    try {
      final rows = await q();
      final list = rows.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      await p.setString('cache_$key', jsonEncode(list));
      return list;
    } catch (_) {
      final s = p.getString('cache_$key');
      if (s == null) rethrow;
      offline = true;
      return (jsonDecode(s) as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
  }

  Future<List<Json>> models() =>
      _get('models', () async => await _c.from('models').select().order('name'));
  Future<List<Json>> offers() =>
      _get('offers', () async => await _c.from('offers').select().limit(5000));
  Future<List<Json>> thresholds() =>
      _get('thresholds', () async => await _c.from('user_thresholds').select());
  Future<List<Json>> alerts() => _get('alerts',
      () async => await _c.from('alerts').select().order('sent_at', ascending: false).limit(200));
  Future<List<Json>> settings() =>
      _get('settings', () async => await _c.from('settings').select());
  Future<List<Json>> snapshots(String modelId) => _get(
      'snap_$modelId',
      () async => await _c
          .from('price_snapshots')
          .select()
          .eq('model_id', modelId)
          .order('fetched_at')
          .limit(3000));

  Future<void> setTracked(String id, bool v) async {
    await _c.from('models').update({'tracked': v}).eq('model_id', id);
    if (v) await _c.from('user_thresholds').upsert({'model_id': id});
  }

  Future<void> saveThreshold(String id,
      {double? target, double? minDiscount, required bool enabled, required bool paused}) async {
    await _c.from('user_thresholds').upsert({
      'model_id': id,
      'target_price': target,
      'min_discount_pct': minDiscount,
      'alerts_enabled': enabled,
      'paused': paused,
    });
  }

  Future<void> setGlobalPause(bool v) async {
    await _c.from('settings').upsert({'key': 'paused', 'value': v});
  }
}

class Best {
  final Json offer;
  final double price;
  final double? ref;
  final String refKind;
  Best(this.offer, this.price, this.ref, this.refKind);
  double? get discountPct => (ref != null && ref! > price) ? (ref! - price) / ref! * 100 : null;
}

/// Shared app state; screens listen with ListenableBuilder.
class AppState extends ChangeNotifier {
  static final AppState i = AppState._();
  AppState._();

  List<Json> models = [], offers = [], thresholds = [], alerts = [];
  bool paused = false, loading = false, offline = false;
  String? error;

  Future<void> load() async {
    loading = true;
    error = null;
    Repo.i.offline = false;
    notifyListeners();
    try {
      final r = Repo.i;
      final res = await Future.wait([r.models(), r.offers(), r.thresholds(), r.alerts(), r.settings()]);
      models = res[0];
      offers = res[1];
      thresholds = res[2];
      alerts = res[3];
      paused = res[4].any((s) => (s['key'] == 'paused' || s['key'] == 'stopped') && s['value'] == true);
      offline = r.offline;
    } catch (e) {
      error = e.toString();
    }
    loading = false;
    notifyListeners();
  }

  List<Json> get tracked => models.where((m) => m['tracked'] == true).toList();

  List<Json> offersOf(String id) {
    final l = offers.where((o) => o['model_id'] == id && o['price'] != null).toList();
    l.sort((a, b) => num_(a['price'])!.compareTo(num_(b['price'])!));
    return l;
  }

  Json? thOf(String id) {
    for (final t in thresholds) {
      if (t['model_id'] == id) return t;
    }
    return null;
  }

  Best? bestOf(String id) {
    final l = offersOf(id);
    if (l.isEmpty) return null;
    final o = l.first;
    final price = num_(o['price'])!;
    final omni = num_(o['lowest_30d']);
    if (omni != null) return Best(o, price, omni, 'Omnibus 30 dana');
    if (l.length >= 3) {
      final ps = l.map((x) => num_(x['price'])!).toList()..sort();
      return Best(o, price, ps[ps.length ~/ 2], 'medijan shopova');
    }
    return Best(o, price, null, '');
  }

  String lastSeen(String id) {
    String? mx;
    for (final o in offers) {
      if (o['model_id'] == id) {
        final s = o['last_seen'] as String?;
        if (s != null && (mx == null || s.compareTo(mx) > 0)) mx = s;
      }
    }
    return ago(mx);
  }

  /// 🎯 below my target, 🔥 new low / ⚠️ suspicious discount in the last 72 h (from the alerts table)
  String badges(String id) {
    final b = StringBuffer();
    final best = bestOf(id);
    final target = num_(thOf(id)?['target_price']);
    if (best != null && target != null && best.price <= target) b.write('🎯');
    final cut = DateTime.now().subtract(const Duration(hours: 72));
    for (final a in alerts) {
      if (a['model_id'] != id) continue;
      final t = DateTime.tryParse('${a['sent_at']}');
      if (t == null || t.isBefore(cut)) continue;
      if (a['rule'] == 'new_low' && !b.toString().contains('🔥')) b.write('🔥');
      if (a['rule'] == 'fake_discount' && !b.toString().contains('⚠️')) b.write('⚠️');
    }
    return b.toString();
  }

  Json? modelById(String id) {
    for (final m in models) {
      if (m['model_id'] == id) return m;
    }
    return null;
  }
}
