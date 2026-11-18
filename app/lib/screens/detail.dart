import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data.dart';

class DetailScreen extends StatefulWidget {
  final String modelId;
  const DetailScreen({super.key, required this.modelId});

  @override
  State<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends State<DetailScreen> {
  List<Json> _snaps = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await Repo.i.snapshots(widget.modelId);
      if (mounted) setState(() => _snaps = s);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _open(String? url) async {
    if (url == null || url.isEmpty) return;
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final st = AppState.i;
    final m = st.modelById(widget.modelId);
    if (m == null) return const Scaffold(body: Center(child: Text('Model nije pronađen')));
    final offers = st.offersOf(widget.modelId);
    final specs = Map<String, dynamic>.from((m['specs'] as Map?) ?? {});
    return Scaffold(
      appBar: AppBar(title: Text('${m['name']}', overflow: TextOverflow.ellipsis)),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Text('Povijest cijena po shopu', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SizedBox(height: 240, child: _loading ? const Center(child: CircularProgressIndicator()) : _chart()),
          const SizedBox(height: 16),
          Text('Trenutne ponude (${offers.length})', style: Theme.of(context).textTheme.titleMedium),
          for (final o in offers)
            Card(
              child: ListTile(
                title: Text('${o['shop']}'),
                subtitle: Text([
                  if (o['old_price'] != null) 'stara ${eur(num_(o['old_price']))}',
                  if (o['lowest_30d'] != null) 'najniža 30 d: ${eur(num_(o['lowest_30d']))}',
                  if (o['verified_direct'] != true) 'cijena preko usporednika, provjeri na shopu prije kupnje',
                ].join(' · ')),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(eur(num_(o['price'])), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(width: 6),
                    IconButton(
                      icon: const Icon(Icons.open_in_new),
                      tooltip: 'Otvori u pregledniku',
                      onPressed: () => _open(o['url'] as String?),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 16),
          Text('Specifikacije', style: Theme.of(context).textTheme.titleMedium),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Dough score: ${m['dough_score'] ?? '?'} (potpunost podataka ${m['completeness'] ?? '?'})'),
                  Text('Snaga: ${specs['power_w'] ?? 'nepoznato'} W'),
                  Text('Posuda: ${specs['bowl_l'] ?? 'nepoznato'} l'),
                  Text('Planetarno miješanje: ${specs['planetary'] == true ? 'da' : 'nije navedeno'}'),
                  Text('Metalno kućište/prijenos: ${(specs['body'] == 'metal' || specs['metal_gears'] == true) ? 'da' : 'nije potvrđeno'}'),
                  if (specs['speeds'] != null) Text('Brzina: ${specs['speeds']}'),
                  const SizedBox(height: 6),
                  Text('Izvor specifikacija: opisi ponuda (Nabava.net/shopovi), ne proizvođač.',
                      style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
          ),
          if (m['best_buy_note'] != null) ...[
            const SizedBox(height: 12),
            Text('Zašto je best buy', style: Theme.of(context).textTheme.titleMedium),
            Card(child: Padding(padding: const EdgeInsets.all(12), child: Text('${m['best_buy_note']}'))),
          ],
        ],
      ),
    );
  }

  Widget _chart() {
    // group snapshots by shop; show the 6 shops with the lowest latest price
    final byShop = <String, List<Json>>{};
    for (final s in _snaps) {
      byShop.putIfAbsent('${s['shop']}', () => []).add(s);
    }
    if (byShop.isEmpty) return const Center(child: Text('Povijest se tek skuplja (nakon prvih runova).'));
    DateTime t0 = DateTime.now();
    for (final s in _snaps) {
      final t = DateTime.tryParse('${s['fetched_at']}');
      if (t != null && t.isBefore(t0)) t0 = t;
    }
    final shops = byShop.keys.toList()
      ..sort((a, b) => num_(byShop[a]!.last['price'])!.compareTo(num_(byShop[b]!.last['price'])!));
    final colors = [Colors.orange, Colors.cyan, Colors.lightGreen, Colors.pinkAccent, Colors.amber, Colors.purpleAccent];
    final bars = <LineChartBarData>[];
    double minY = double.infinity, maxY = 0, maxX = 1;
    for (var i = 0; i < shops.length && i < 6; i++) {
      final spots = <FlSpot>[];
      for (final s in byShop[shops[i]]!) {
        final t = DateTime.tryParse('${s['fetched_at']}');
        final p = num_(s['price']);
        if (t == null || p == null) continue;
        final x = t.difference(t0).inMinutes / 60.0;
        spots.add(FlSpot(x, p));
        if (p < minY) minY = p;
        if (p > maxY) maxY = p;
        if (x > maxX) maxX = x;
      }
      bars.add(LineChartBarData(
        spots: spots,
        isCurved: false,
        color: colors[i],
        barWidth: 2,
        dotData: FlDotData(show: spots.length < 4),
      ));
    }
    if (bars.isEmpty) return const Center(child: Text('Nema podataka'));
    final pad = (maxY - minY) * 0.1 + 5;
    return Column(
      children: [
        Expanded(
          child: LineChart(
            LineChartData(
              minY: minY - pad,
              maxY: maxY + pad,
              minX: 0,
              maxX: maxX,
              lineBarsData: bars,
              gridData: FlGridData(show: true),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 24,
                    interval: maxX > 1 ? maxX / 4 : 1,
                    getTitlesWidget: (value, meta) {
                      final d = t0.add(Duration(minutes: (value * 60).round()));
                      return Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text('${d.day}.${d.month}.', style: const TextStyle(fontSize: 10)),
                      );
                    },
                  ),
                ),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 44,
                    getTitlesWidget: (value, meta) =>
                        Text(value.toStringAsFixed(0), style: const TextStyle(fontSize: 10)),
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 10,
          children: [
            for (var i = 0; i < shops.length && i < 6; i++)
              Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.circle, size: 10, color: colors[i]),
                const SizedBox(width: 4),
                Text(shops[i], style: const TextStyle(fontSize: 11)),
              ]),
          ],
        ),
      ],
    );
  }
}
