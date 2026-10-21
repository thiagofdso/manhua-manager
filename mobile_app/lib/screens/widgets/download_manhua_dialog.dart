import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';
import '../../models/download_task.dart';
import '../../models/manhua.dart';
import '../../services/download_manager.dart';
import '../../services/download_service.dart';

class DownloadManhuaDialog extends StatefulWidget {
  final Manhua manhua;
  final DownloadService? downloadService;
  final DownloadManager? downloadManager;

  const DownloadManhuaDialog({
    super.key,
    required this.manhua,
    this.downloadService,
    this.downloadManager,
  });

  @override
  State<DownloadManhuaDialog> createState() => _DownloadManhuaDialogState();
}

class _DownloadManhuaDialogState extends State<DownloadManhuaDialog> {
  late final DownloadService _downloadService;
  late final TextEditingController _startController;
  late final TextEditingController _endController;

  List<int> _downloadedChapters = [];
  int? _lastObservedChapter;

  @override
  void initState() {
    super.initState();
    _downloadService = widget.downloadService ?? DownloadService();
    final startChap = widget.manhua.currentChapter > 0 ? widget.manhua.currentChapter : 1;
    _startController = TextEditingController(text: startChap.toString());
    _endController = TextEditingController(text: (startChap + 4).toString());
    _loadDownloadedChapters();
  }

  @override
  void dispose() {
    _startController.dispose();
    _endController.dispose();
    super.dispose();
  }

  Future<void> _loadDownloadedChapters() async {
    final list = await _downloadService.getDownloadedChapters(widget.manhua.id);
    if (mounted) {
      setState(() {
        _downloadedChapters = list;
      });
    }
  }

  Future<void> _deleteChapter(int chapter) async {
    await _downloadService.deleteChapter(widget.manhua.id, chapter);
    await _loadDownloadedChapters();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Capítulo $chapter excluído localmente.')),
      );
    }
  }

  Future<void> _deleteAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Excluir Todos os Downloads'),
        content: Text('Deseja excluir todos os capítulos baixados de "${widget.manhua.title}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Excluir', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _downloadService.deleteAllForManhua(widget.manhua.id);
      await _loadDownloadedChapters();
    }
  }

  void _startDownload(DownloadManager downloadManager) {
    final start = int.tryParse(_startController.text.trim());
    final end = int.tryParse(_endController.text.trim());

    if (start == null || end == null || start < 1 || end < start) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, informe um intervalo válido (Início >= 1 e <= Fim).')),
      );
      return;
    }

    if ((end - start + 1) > 50) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('O limite máximo por lote é de 50 capítulos.')),
      );
      return;
    }

    final controller = context.read<ManhuaController>();
    downloadManager.startDownload(
      manhua: widget.manhua,
      startChapter: start,
      endChapter: end,
      apiService: controller.apiService,
      downloadService: _downloadService,
    ).then((_) {
      _loadDownloadedChapters();
    });
  }

  @override
  Widget build(BuildContext context) {
    final downloadManager = widget.downloadManager ?? Provider.of<DownloadManager>(context);
    final task = downloadManager.getTask(widget.manhua.id);
    final isDownloading = task != null && !task.isCancelled && task.status == DownloadTaskStatus.downloading;

    // Se o capítulo em download mudou ou a tarefa concluiu, atualiza a lista de capítulos salvos
    if (task != null && task.currentChapter != _lastObservedChapter) {
      _lastObservedChapter = task.currentChapter;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _loadDownloadedChapters();
      });
    }

    return AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.download_rounded, color: Color(0xFF8257E6)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Downloads: ${widget.manhua.title}',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Intervalo de Capítulos:', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _startController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Do Capítulo',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      enabled: !isDownloading,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: _endController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Até o Capítulo',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      enabled: !isDownloading,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (isDownloading)
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.redAccent,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(40),
                  ),
                  onPressed: () => downloadManager.cancelDownload(widget.manhua.id),
                  icon: const Icon(Icons.cancel_outlined),
                  label: const Text('Cancelar Download'),
                )
              else
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF8257E6),
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(40),
                  ),
                  onPressed: () => _startDownload(downloadManager),
                  icon: const Icon(Icons.cloud_download),
                  label: const Text('Iniciar Download'),
                ),
              if (task != null) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: isDownloading
                      ? (task.progress > 0 ? task.progress : null)
                      : (task.status == DownloadTaskStatus.completed ? 1.0 : task.progress),
                  backgroundColor: const Color(0xFF323238),
                  color: (task.status == DownloadTaskStatus.cancelled || task.status == DownloadTaskStatus.error)
                      ? Colors.redAccent
                      : const Color(0xFF8257E6),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        task.statusMessage,
                        style: TextStyle(
                          fontSize: 12,
                          color: (task.status == DownloadTaskStatus.cancelled || task.status == DownloadTaskStatus.error)
                              ? Colors.redAccent
                              : Colors.grey,
                        ),
                      ),
                    ),
                    if (isDownloading && task.progress > 0)
                      Text(
                        '${(task.progress * 100).toInt()}%',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey),
                      ),
                  ],
                ),
              ],
              const Divider(height: 28),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Capítulos Salvos (${_downloadedChapters.length})',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                  if (_downloadedChapters.isNotEmpty)
                    TextButton(
                      style: TextButton.styleFrom(foregroundColor: Colors.redAccent),
                      onPressed: isDownloading ? null : _deleteAll,
                      child: const Text('Excluir Todos', style: TextStyle(fontSize: 12)),
                    ),
                ],
              ),
              const SizedBox(height: 4),
              if (_downloadedChapters.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.0),
                  child: Text(
                    'Nenhum capítulo salvo localmente para esta obra.',
                    style: TextStyle(color: Colors.grey, fontSize: 12),
                  ),
                )
              else
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 180),
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: _downloadedChapters.length,
                    itemBuilder: (ctx, idx) {
                      final chap = _downloadedChapters[idx];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF29292E),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Capítulo $chap', style: const TextStyle(fontWeight: FontWeight.w500)),
                            IconButton(
                              icon: const Icon(Icons.delete_outline, size: 18, color: Colors.redAccent),
                              tooltip: 'Excluir capítulo',
                              onPressed: isDownloading ? null : () => _deleteChapter(chap),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Fechar'),
        ),
      ],
    );
  }
}
