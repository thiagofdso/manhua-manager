import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';

class AddManhuaDialog extends StatefulWidget {
  const AddManhuaDialog({super.key});

  @override
  State<AddManhuaDialog> createState() => _AddManhuaDialogState();
}

class _AddManhuaDialogState extends State<AddManhuaDialog> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _urlController = TextEditingController();
  final _chapterController = TextEditingController();

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
      final reg = RegExp('(?<=[^0-9]|^)$chapter(?=[^0-9]|\$)');
      if (reg.hasMatch(rawUrl)) {
        urlTemplate = rawUrl.replaceFirst(reg, '{chapter}');
      }
    }

    await context.read<ManhuaController>().addManhua(title, urlTemplate, chapter);

    if (mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Obra "$title" cadastrada com sucesso!')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Cadastrar Nova Obra'),
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
                  hintText: 'Ex: Overgeared',
                  border: OutlineInputBorder(),
                ),
                validator: (val) =>
                    val == null || val.trim().isEmpty ? 'Informe o título' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _urlController,
                decoration: const InputDecoration(
                  labelText: 'URL do Capítulo Atual',
                  hintText: 'Ex: https://asurascans.com/.../chapter/203',
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
                  labelText: 'Capítulo Inicial',
                  hintText: 'Ex: 203',
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
