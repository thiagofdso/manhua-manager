import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';
import '../../models/manhua.dart';
import '../../services/download_service.dart';

class DownloadManhuaDialog extends StatefulWidget {
  final Manhua manhua;
  final DownloadService? downloadService;

  const DownloadManhuaDialog({
    super.key,
    required this.manhua,
    this.downloadService,
  });

  @override
  State<DownloadManhuaDialog> createState() => _DownloadManhuaDialogState();
}

class _DownloadManhuaDialogState extends State<DownloadManhuaDialog> {
  late final DownloadService _downloadService;
  late final TextEditingController _startController;
  late final TextEditingController _endController;

  bool _isDownloading = false;
  String _progressText = '';
  double _progressValue = 0.0;
  List<int> _downloadedChapters = [];

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

  Future<void> _startDownload() async {
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

    setState(() {
      _isDownloading = true;
      _progressText = 'Consultando capítulos no servidor...';
      _progressValue = 0.05;
    });

    final controller = context.read<ManhuaController>();

    try {
      final batchData = await controller.apiService.fetchBatchChapterImages(widget.manhua.id, start, end);
      final List<dynamic> chapters = batchData['chapters'] ?? [];

      int totalImages = 0;
      for (final c in chapters) {
        final List<dynamic> imgs = c['images'] ?? [];
        totalImages += imgs.length;
      }

      int downloadedImages = 0;

      for (int i = 0; i < chapters.length; i++) {
        final c = chapters[i];
        final chapNum = c['chapter'] as int;
        final List<dynamic> images = c['images'] ?? [];

        if (images.isEmpty) continue;

        for (int p = 0; p < images.length; p++) {
          final imgUrl = images[p].toString();
          if (mounted) {
            setState(() {
              _progressText = 'Capítulo $chapNum: imagem ${p + 1} de ${images.length}...';
            });
          }

          try {
            final proxy = await controller.apiService.getProxyImageUrl(imgUrl);
            final bytes = await controller.apiService.downloadImageBytes(proxy);
            await _downloadService.saveChapterImage(widget.manhua.id, chapNum, p, bytes);
          } catch (e) {
            debugPrint('Erro ao baixar imagem: $e');
          }

          downloadedImages++;
          if (mounted && totalImages > 0) {
            setState(() {
              _progressValue = downloadedImages / totalImages;
            });
          }
        }
        await _loadDownloadedChapters();
      }

      if (mounted) {
        setState(() {
          _progressText = 'Download finalizado!';
          _progressValue = 1.0;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Capítulos baixados com sucesso!')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _progressText = 'Erro ao baixar: $e';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro durante o download: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isDownloading = false;
        });
        await _loadDownloadedChapters();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
                      enabled: !_isDownloading,
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
                      enabled: !_isDownloading,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF8257E6),
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(40),
                ),
                onPressed: _isDownloading ? null : _startDownload,
                icon: const Icon(Icons.cloud_download),
                label: const Text('Iniciar Download'),
              ),
              if (_isDownloading || _progressText.isNotEmpty) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: _isDownloading ? _progressValue : null,
                  backgroundColor: const Color(0xFF323238),
                  color: const Color(0xFF8257E6),
                ),
                const SizedBox(height: 6),
                Text(
                  _progressText,
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
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
                      onPressed: _isDownloading ? null : _deleteAll,
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
                              onPressed: _isDownloading ? null : () => _deleteChapter(chap),
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
