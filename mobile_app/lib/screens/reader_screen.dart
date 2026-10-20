import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/manhua_controller.dart';
import '../models/manhua.dart';

class ReaderScreen extends StatefulWidget {
  final Manhua manhua;

  const ReaderScreen({super.key, required this.manhua});

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends State<ReaderScreen> {
  late int _currentChapter;
  bool _isLoading = true;
  String? _errorMessage;
  List<String> _imageUrls = [];
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _currentChapter = widget.manhua.currentChapter;
    _loadPages();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPages() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _imageUrls = [];
    });

    if (_scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }

    try {
      final controller = context.read<ManhuaController>();
      final targetUrl = widget.manhua.targetUrlForChapter(_currentChapter);
      final rawImages = await controller.apiService.fetchChapterImages(targetUrl);

      final List<String> proxyImages = [];
      for (final img in rawImages) {
        final proxy = await controller.apiService.getProxyImageUrl(img);
        proxyImages.add(proxy);
      }

      if (mounted) {
        setState(() {
          _imageUrls = proxyImages;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _changeChapter(int delta) async {
    final nextChapter = _currentChapter + delta;
    if (nextChapter < 1) return;

    setState(() {
      _currentChapter = nextChapter;
    });

    // Atualiza o progresso no backend
    context.read<ManhuaController>().changeChapterDelta(widget.manhua.id, delta);

    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Carregando Capítulo $_currentChapter...'),
        duration: const Duration(seconds: 1),
      ),
    );

    await _loadPages();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          '${widget.manhua.title} $_currentChapter',
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Recarregar páginas',
            onPressed: _loadPages,
          ),
        ],
      ),
      body: GestureDetector(
        // Navegação por clique e arrasto (swipe horizontal)
        onHorizontalDragEnd: (DragEndDetails details) {
          final velocity = details.primaryVelocity ?? 0;
          if (velocity < -300) {
            // Deslizar da direita para a esquerda: Próximo capítulo
            _changeChapter(1);
          } else if (velocity > 300) {
            // Deslizar da esquerda para a direita: Capítulo anterior
            _changeChapter(-1);
          }
        },
        child: _buildBody(),
      ),
      bottomNavigationBar: Container(
        color: const Color(0xFF202024),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: SafeArea(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF323238),
                  foregroundColor: Colors.white,
                ),
                onPressed: _currentChapter > 1 ? () => _changeChapter(-1) : null,
                icon: const Icon(Icons.arrow_back, size: 16),
                label: const Text('Anterior'),
              ),
              Text(
                'Capítulo $_currentChapter',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF8257E6),
                  foregroundColor: Colors.white,
                ),
                onPressed: () => _changeChapter(1),
                icon: const Icon(Icons.arrow_forward, size: 16),
                label: const Text('Próximo'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Color(0xFF8257E6)),
            SizedBox(height: 16),
            Text('Carregando páginas do capítulo...'),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.redAccent),
              const SizedBox(height: 16),
              Text(
                'Erro ao carregar capítulo:\n$_errorMessage',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.redAccent),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF8257E6)),
                onPressed: _loadPages,
                icon: const Icon(Icons.refresh, color: Colors.white),
                label: const Text('Tentar Novamente', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );
    }

    if (_imageUrls.isEmpty) {
      return const Center(
        child: Text('Nenhuma imagem encontrada para este capítulo.'),
      );
    }

    // Leitor contínuo estilo Webtoon (vertical sem espaçamento)
    return ListView.builder(
      controller: _scrollController,
      padding: EdgeInsets.zero,
      itemCount: _imageUrls.length,
      itemBuilder: (context, index) {
        final imgUrl = _imageUrls[index];
        return CachedNetworkImage(
          imageUrl: imgUrl,
          fit: BoxFit.fitWidth,
          placeholder: (context, url) => Container(
            height: 350,
            color: const Color(0xFF18181B),
            child: const Center(
              child: SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Color(0xFF8257E6),
                ),
              ),
            ),
          ),
          errorWidget: (context, url, error) => Container(
            height: 150,
            color: const Color(0xFF202024),
            alignment: Alignment.center,
            child: Text(
              'Erro ao exibir página ${index + 1}',
              style: const TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ),
        );
      },
    );
  }
}
