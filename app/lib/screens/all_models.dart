import 'package:flutter/material.dart';

import '../data.dart';
import 'detail.dart';

class AllModelsScreen extends StatefulWidget {
  const AllModelsScreen({super.key});

  @override
  State<AllModelsScreen> createState() => _AllModelsScreenState();
}

class _AllModelsScreenState extends State<AllModelsScreen> {
  String _q = '';
  String? _brand;
  String? _shop;
  RangeValues? _price;
  double _minPower = 0;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.i,
      builder: (context, _) {
        final s = AppState.i;
        // rows: model + its cheapest offer
        final rows = <_Row>[];
        for (final m in s.models) {
          final offers = s.offersOf(m['model_id'] as String);
          if (offers.isEmpty) continue;
          rows.add(_Row(m, offers));
        }
        final brands = (rows.map((r) => '${r.m['brand']}').toSet().toList())..sort();
        final shops = (rows.expand((r) => r.offers.map((o) => '${o['shop']}')).toSet().toList())..sort();
        final prices = rows.map((r) => r.min).toList();
        final lo = prices.isEmpty ? 0.0 : prices.reduce((a, b) => a < b ? a : b).floorToDouble();
        final hi = prices.isEmpty ? 1.0 : prices.reduce((a, b) => a > b ? a : b).ceilToDouble();
        final range = _price ?? RangeValues(lo, hi > lo ? hi : lo + 1);
        final shown = rows.where((r) {
          final specs = (r.m['specs'] as Map?) ?? {};
          final power = num_(specs['power_w']) ?? 0;
          if (_q.isNotEmpty && !'${r.m['name']}'.toLowerCase().contains(_q.toLowerCase())) return false;
          if (_brand != null && r.m['brand'] != _brand) return false;
          if (_shop != null && !r.offers.any((o) => o['shop'] == _shop)) return false;
          if (r.min < range.start || r.min > range.end) return false;
          if (power < _minPower) return false;
          return true;
        }).toList()
          ..sort((a, b) => a.min.compareTo(b.min));

        return Scaffold(
          appBar: AppBar(title: Text('Svi mikseri (${shown.length}/${rows.length})')),
          body: RefreshIndicator(
            onRefresh: s.load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(8),
              children: [
                TextField(
                  decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search), hintText: 'Traži po nazivu', border: OutlineInputBorder()),
                  onChanged: (v) => setState(() => _q = v),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String?>(
                        value: _brand,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'Brend', border: OutlineInputBorder()),
                        items: [
                          const DropdownMenuItem<String?>(value: null, child: Text('Svi')),
                          for (final b in brands) DropdownMenuItem<String?>(value: b, child: Text(b)),
                        ],
                        onChanged: (v) => setState(() => _brand = v),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<String?>(
                        value: _shop,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'Shop', border: OutlineInputBorder()),
                        items: [
                          const DropdownMenuItem<String?>(value: null, child: Text('Svi')),
                          for (final x in shops) DropdownMenuItem<String?>(value: x, child: Text(x)),
                        ],
                        onChanged: (v) => setState(() => _shop = v),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Cijena: ${range.start.round()} do ${range.end.round()} €'),
                RangeSlider(
                  min: lo,
                  max: hi > lo ? hi : lo + 1,
                  values: RangeValues(range.start.clamp(lo, hi > lo ? hi : lo + 1),
                      range.end.clamp(lo, hi > lo ? hi : lo + 1)),
                  onChanged: (v) => setState(() => _price = v),
                ),
                Text('Minimalna snaga: ${_minPower.round()} W'),
                Slider(
                  min: 0,
                  max: 2000,
                  divisions: 20,
                  value: _minPower,
                  onChanged: (v) => setState(() => _minPower = v),
                ),
                const Divider(),
                for (final r in shown) _tile(context, r),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _tile(BuildContext context, _Row r) {
    final id = r.m['model_id'] as String;
    final tracked = r.m['tracked'] == true;
    final specs = (r.m['specs'] as Map?) ?? {};
    return ListTile(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => DetailScreen(modelId: id))),
      title: Text('${r.m['name']}', maxLines: 2, overflow: TextOverflow.ellipsis),
      subtitle: Text('${eur(r.min)} · ${r.offers.first['shop']} · ${specs['power_w'] ?? '?'} W · '
          'dough ${r.m['dough_score'] ?? '?'}'),
      trailing: IconButton(
        icon: Icon(tracked ? Icons.star : Icons.star_border, color: tracked ? Colors.amber : null),
        tooltip: tracked ? 'Makni iz praćenja' : 'Dodaj u praćenje',
        onPressed: () async {
          final messenger = ScaffoldMessenger.of(context);
          try {
            await Repo.i.setTracked(id, !tracked);
            await AppState.i.load();
            messenger.showSnackBar(SnackBar(
                content: Text(tracked
                    ? 'Uklonjeno iz praćenja'
                    : 'Dodano u praćenje. Prve nove cijene stižu pri sljedećem runu (07:00/19:00).')));
          } catch (e) {
            messenger.showSnackBar(SnackBar(content: Text('Greška: $e')));
          }
        },
      ),
    );
  }
}

class _Row {
  final Json m;
  final List<Json> offers;
  _Row(this.m, this.offers);
  double get min => num_(offers.first['price'])!;
}
