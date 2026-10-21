import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';
import '../../models/manhua.dart';

class EditManhuaDialog extends StatefulWidget {
  final Manhua manhua;

  const EditManhuaDialog({super.key, required this.manhua});

  @override
  State<EditManhuaDialog> createState() => _EditManhuaDialogState();
}

class _EditManhuaDialogState extends State<EditManhuaDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _titleController;
  late TextEditingController _urlController;
  late TextEditingController _chapterController;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController(text: widget.manhua.title);
    _urlController = TextEditingController(text: widget.manhua.urlTemplate);
    _chapterController =
        TextEditingController(text: widget.manhua.currentChapter.toString());
  }

  @override
  void dispose() {
    _titleController.dispose();
    _urlController.dispose();
    _chapterController.dispose();
    super.dispose();
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final title = _titleController.text.trim();
    final rawUrl = _urlController.text.trim();
    final chapter = int.parse(_chapterController.text.trim());

    String urlTemplate = rawUrl;
    if (!urlTemplate.contains('{chapter}')) {
      if (rawUrl.contains('mangafire.to')) {
        urlTemplate = rawUrl.replaceFirst(RegExp(r'/chapter/\d+'), '/chapter/{chapter}');
      } else if (rawUrl.contains('comix.to')) {
        urlTemplate = rawUrl.replaceFirst(RegExp(r'/\d+-chapter-\d+'), '/{chapter}');
      } else {
        final reg = RegExp('(?<=[^0-9]|^)$chapter(?=[^0-9]|\$)');
        if (reg.hasMatch(rawUrl)) {
          urlTemplate = rawUrl.replaceFirst(reg, '{chapter}');
        }
      }
    }

    await context.read<ManhuaController>().editManhua(
          widget.manhua.id,
          title: title,
          urlTemplate: urlTemplate,
          chapter: chapter,
        );

    if (mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Obra atualizada com sucesso!')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Editar Obra'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Título do Manhua',
                  border: OutlineInputBorder(),
                ),
                validator: (val) =>
                    val == null || val.trim().isEmpty ? 'Informe o título' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _urlController,
                decoration: const InputDecoration(
                  labelText: 'Template da URL ({chapter})',
                  border: OutlineInputBorder(),
                ),
                validator: (val) =>
                    val == null || val.trim().isEmpty ? 'Informe a URL' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _chapterController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Capítulo Atual',
                  border: OutlineInputBorder(),
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) return 'Informe o capítulo';
                  final n = int.tryParse(val.trim());
                  if (n == null || n < 1) return 'Capítulo inválido';
                  return null;
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF8257E6),
            foregroundColor: Colors.white,
          ),
          onPressed: _submit,
          child: const Text('Salvar'),
        ),
      ],
    );
  }
}
