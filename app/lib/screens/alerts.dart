import 'package:flutter/material.dart';

import '../data.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  static const _icons = {
    'new_low': '🔥',
    'bigger_discount': '📉',
    'below_threshold': '🎯',
    'fake_discount': '⚠️',
    'daily_top': '🏆',
    'health': '🛠',
  };

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.i,
      builder: (context, _) {
        final s = AppState.i;
        return Scaffold(
          appBar: AppBar(title: Text('Povijest alarma (${s.alerts.length})')),
          body: RefreshIndicator(
            onRefresh: s.load,
            child: s.alerts.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: const [Padding(padding: EdgeInsets.all(32), child: Center(child: Text('Još nema alarma.')))],
                  )
                : ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    itemCount: s.alerts.length,
                    itemBuilder: (context, i) {
                      final a = s.alerts[i];
                      final model = s.modelById('${a['model_id']}');
                      final msg = stripHtml('${a['message'] ?? ''}');
                      return ExpansionTile(
                        leading: Text(_icons['${a['rule']}'] ?? '•', style: const TextStyle(fontSize: 22)),
                        title: Text('${model?['name'] ?? a['shop'] ?? a['rule']}', maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text([
                          if (a['shop'] != null) '${a['shop']}',
                          if (a['price'] != null) eur(num_(a['price'])),
                          ago('${a['sent_at']}'),
                          if (a['telegram_ok'] == false) 'Telegram: nije poslano',
                        ].join(' · ')),
                        children: [Padding(padding: const EdgeInsets.all(12), child: Text(msg))],
                      );
                    },
                  ),
          ),
        );
      },
    );
  }
}
