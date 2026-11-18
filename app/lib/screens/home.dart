import 'package:flutter/material.dart';

import '../data.dart';
import 'detail.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.i,
      builder: (context, _) {
        final s = AppState.i;
        final items = s.tracked;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Pregled'),
            actions: [
              if (s.paused)
                const Padding(
                  padding: EdgeInsets.only(right: 12),
                  child: Chip(label: Text('⏸ pauzirano')),
                ),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: s.load,
            child: items.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(32),
                        child: Center(
                          child: Text(s.loading
                              ? 'Učitavanje...'
                              : s.error != null
                                  ? 'Greška: ${s.error}'
                                  : 'Nema praćenih modela. Dodaj ih u "Svi".'),
                        ),
                      ),
                    ],
                  )
                : ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(8),
                    itemCount: items.length,
                    itemBuilder: (context, i) => _ModelCard(model: items[i]),
                  ),
          ),
        );
      },
    );
  }
}

class _ModelCard extends StatelessWidget {
  final Json model;
  const _ModelCard({required this.model});

  @override
  Widget build(BuildContext context) {
    final s = AppState.i;
    final id = model['model_id'] as String;
    final best = s.bestOf(id);
    final badges = s.badges(id);
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: InkWell(
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => DetailScreen(modelId: id))),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text('${model['name']}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  ),
                  if (badges.isNotEmpty) Text(badges, style: const TextStyle(fontSize: 20)),
                ],
              ),
              const SizedBox(height: 8),
              if (best == null)
                const Text('Nema ponuda')
              else ...[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(eur(best.price),
                        style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: scheme.primary)),
                    const SizedBox(width: 10),
                    Expanded(child: Text('${best.offer['shop']}', overflow: TextOverflow.ellipsis)),
                  ],
                ),
                const SizedBox(height: 4),
                Text(best.discountPct != null
                    ? 'Stvarni popust: ${best.discountPct!.toStringAsFixed(1)}% (${best.refKind})'
                    : 'Nema pouzdane reference za stvarni popust'),
                if (best.offer['verified_direct'] != true)
                  Text('Cijena preko usporednika, provjeri na shopu',
                      style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant)),
              ],
              const SizedBox(height: 4),
              Text('Ažurirano: ${s.lastSeen(id)}',
                  style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant)),
            ],
          ),
        ),
      ),
    );
  }
}
