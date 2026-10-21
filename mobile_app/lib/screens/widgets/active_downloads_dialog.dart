import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/download_manager.dart';

class ActiveDownloadsDialog extends StatelessWidget {
  final DownloadManager? downloadManager;

  const ActiveDownloadsDialog({super.key, this.downloadManager});

  @override
  Widget build(BuildContext context) {
    final manager = downloadManager ?? Provider.of<DownloadManager>(context);

    return ListenableBuilder(
      listenable: manager,
      builder: (context, _) {
        final activeTasks = manager.activeTasks;

        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.downloading, color: Color(0xFF8257E6)),
              SizedBox(width: 8),
              Text(
                'Downloads em Andamento',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SizedBox(
            width: double.maxFinite,
            child: activeTasks.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24.0),
                    child: Text(
                      'Nenhum download em andamento no momento.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey, fontSize: 13),
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: activeTasks.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (ctx, idx) {
                      final task = activeTasks[idx];
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF202024),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF323238)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    task.manhuaTitle,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.redAccent,
                                    side: const BorderSide(color: Colors.redAccent),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    minimumSize: Size.zero,
                                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  ),
                                  onPressed: () => manager.cancelDownload(task.manhuaId),
                                  child: const Text('Cancelar', style: TextStyle(fontSize: 12)),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            LinearProgressIndicator(
                              value: task.progress > 0 ? task.progress : null,
                              backgroundColor: const Color(0xFF323238),
                              color: const Color(0xFF8257E6),
                            ),
                            const SizedBox(height: 6),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    task.statusMessage,
                                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (task.progress > 0)
                                  Text(
                                    '${(task.progress * 100).toInt()}%',
                                    style: const TextStyle(
                                        fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Fechar'),
            ),
          ],
        );
      },
    );
  }
}
