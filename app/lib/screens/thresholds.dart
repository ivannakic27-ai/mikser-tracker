import 'package:flutter/material.dart';

import '../data.dart';

class ThresholdsScreen extends StatelessWidget {
  const ThresholdsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.i,
      builder: (context, _) {
        final s = AppState.i;
        return Scaffold(
          appBar: AppBar(title: const Text('Pragovi i postavke')),
          body: RefreshIndicator(
            onRefresh: s.load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                SwitchListTile(
                  title: const Text('Pauziraj cijelo praćenje'),
                  subtitle: const Text('Scraper preskače runove dok je uključeno (isto kao /pauza u Telegramu)'),
                  value: s.paused,
                  onChanged: (v) async {
                    final messenger = ScaffoldMessenger.of(context);
                    try {
                      await Repo.i.setGlobalPause(v);
                      await s.load();
                    } catch (e) {
                      messenger.showSnackBar(SnackBar(content: Text('Greška: $e')));
                    }
                  },
                ),
                const Divider(),
                for (final m in s.tracked) _tile(context, m, s),
                if (s.tracked.isEmpty)
                  const Padding(padding: EdgeInsets.all(24), child: Text('Nema praćenih modela.')),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _tile(BuildContext context, Json m, AppState s) {
    final id = m['model_id'] as String;
    final th = s.thOf(id);
    final target = num_(th?['target_price']);
    final minDisc = num_(th?['min_discount_pct']);
    final enabled = th?['alerts_enabled'] != false;
    final paused = th?['paused'] == true;
    return ListTile(
      title: Text('${m['name']}', maxLines: 2, overflow: TextOverflow.ellipsis),
      subtitle: Text([
        'cilj: ${target == null ? 'nije postavljen' : eur(target)}',
        if (minDisc != null) 'popust ≥ ${minDisc.toStringAsFixed(0)} %',
        if (!enabled) 'alarmi isključeni',
        if (paused) 'pauzirano',
      ].join(' · ')),
      trailing: const Icon(Icons.edit),
      onTap: () => showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (_) => _Editor(modelId: id, name: '${m['name']}', target: target, minDisc: minDisc, enabled: enabled, paused: paused),
      ),
    );
  }
}

class _Editor extends StatefulWidget {
  final String modelId, name;
  final double? target, minDisc;
  final bool enabled, paused;
  const _Editor(
      {required this.modelId,
      required this.name,
      required this.target,
      required this.minDisc,
      required this.enabled,
      required this.paused});

  @override
  State<_Editor> createState() => _EditorState();
}

class _EditorState extends State<_Editor> {
  late final TextEditingController _target =
      TextEditingController(text: widget.target?.toStringAsFixed(0) ?? '');
  late final TextEditingController _disc =
      TextEditingController(text: widget.minDisc?.toStringAsFixed(0) ?? '');
  late bool _enabled = widget.enabled;
  late bool _paused = widget.paused;
  bool _busy = false;

  double? _parse(String s) => s.trim().isEmpty ? null : double.tryParse(s.trim().replaceAll(',', '.'));

  Future<void> _save() async {
    setState(() => _busy = true);
    final nav = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      await Repo.i.saveThreshold(widget.modelId,
          target: _parse(_target.text), minDiscount: _parse(_disc.text), enabled: _enabled, paused: _paused);
      await AppState.i.load();
      nav.pop();
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Greška: $e')));
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(widget.name, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            controller: _target,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Ciljna cijena (€)', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _disc,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Minimalni stvarni popust (%)', border: OutlineInputBorder()),
          ),
          SwitchListTile(
              title: const Text('Alarmi uključeni'), value: _enabled, onChanged: (v) => setState(() => _enabled = v)),
          SwitchListTile(
              title: const Text('Pauziraj praćenje ovog modela'),
              value: _paused,
              onChanged: (v) => setState(() => _paused = v)),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Spremam...' : 'Spremi')),
          ),
        ],
      ),
    );
  }
}
