import 'package:flutter/material.dart';

import '../data.dart';

class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key});

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  final List<String> _sel = [];

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.i,
      builder: (context, _) {
        final s = AppState.i;
        final models = s.models.where((m) => s.offersOf(m['model_id'] as String).isNotEmpty).toList();
        final chosen = _sel.map((id) => s.modelById(id)).whereType<Json>().toList();
        return Scaffold(
          appBar: AppBar(title: const Text('Usporedba (2 do 3 modela)')),
          body: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final m in s.tracked)
                    FilterChip(
                      label: Text('${m['name']}'.split(' ').take(3).join(' ')),
                      selected: _sel.contains(m['model_id']),
                      onSelected: (v) => setState(() {
                        final id = m['model_id'] as String;
                        if (v && _sel.length < 3) {
                          _sel.add(id);
                        } else {
                          _sel.remove(id);
                        }
                      }),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: null,
                isExpanded: true,
                decoration: const InputDecoration(
                    labelText: 'Dodaj bilo koji model...', border: OutlineInputBorder()),
                items: [
                  for (final m in models)
                    DropdownMenuItem<String>(
                        value: m['model_id'] as String, child: Text('${m['name']}', overflow: TextOverflow.ellipsis)),
                ],
                onChanged: (v) {
                  if (v != null && _sel.length < 3 && !_sel.contains(v)) setState(() => _sel.add(v));
                },
              ),
              const SizedBox(height: 16),
              if (chosen.length < 2)
                const Text('Odaberi barem 2 modela.')
              else
                _table(chosen, s),
            ],
          ),
        );
      },
    );
  }

  Widget _table(List<Json> chosen, AppState s) {
    String specStr(Json m, String key, [String suffix = '']) {
      final v = ((m['specs'] as Map?) ?? {})[key];
      return v == null ? '?' : '$v$suffix';
    }

    bool metal(Json m) {
      final sp = (m['specs'] as Map?) ?? {};
      return sp['body'] == 'metal' || sp['metal_gears'] == true;
    }

    final rows = <String, List<String>>{
      'Najniža cijena': [for (final m in chosen) eur(s.bestOf(m['model_id'] as String)?.price)],
      'Shop': [for (final m in chosen) '${s.bestOf(m['model_id'] as String)?.offer['shop'] ?? '?'}'],
      'Stvarni popust': [
        for (final m in chosen)
          s.bestOf(m['model_id'] as String)?.discountPct == null
              ? 'nema reference'
              : '${s.bestOf(m['model_id'] as String)!.discountPct!.toStringAsFixed(1)} %'
      ],
      'Dough score': [for (final m in chosen) '${m['dough_score'] ?? '?'}'],
      'Snaga': [for (final m in chosen) specStr(m, 'power_w', ' W')],
      'Posuda': [for (final m in chosen) specStr(m, 'bowl_l', ' l')],
      'Planetarno': [
        for (final m in chosen) (((m['specs'] as Map?) ?? {})['planetary'] == true) ? 'da' : 'nije navedeno'
      ],
      'Metal': [for (final m in chosen) metal(m) ? 'da' : 'nije potvrđeno'],
      'Broj shopova': [for (final m in chosen) '${s.offersOf(m['model_id'] as String).length}'],
    };
    return Table(
      border: TableBorder.all(color: Colors.white24),
      columnWidths: const {0: FixedColumnWidth(110)},
      defaultVerticalAlignment: TableCellVerticalAlignment.middle,
      children: [
        TableRow(children: [
          const SizedBox.shrink(),
          for (final m in chosen)
            Padding(
              padding: const EdgeInsets.all(6),
              child: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
            ),
        ]),
        for (final e in rows.entries)
          TableRow(children: [
            Padding(padding: const EdgeInsets.all(6), child: Text(e.key, style: const TextStyle(fontSize: 12))),
            for (final v in e.value) Padding(padding: const EdgeInsets.all(6), child: Text(v)),
          ]),
      ],
    );
  }
}
