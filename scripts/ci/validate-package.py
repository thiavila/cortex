"""Dependency-free package contract checks shared by local and official CI."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
claude = json.loads((root / '.claude-plugin/plugin.json').read_text())
codex = json.loads((root / '.codex-plugin/plugin.json').read_text())
assert claude['version'] == codex['version'], 'Plugin versions differ'
assert codex['name'] == claude['name'] == 'cortex'
hooks = json.loads((root / codex['hooks']).read_text())['hooks']
assert set(hooks) == {'SessionStart', 'UserPromptSubmit'}
for name in ('tarefas', 'tarefas-io', 'quadro-tarefas', 'bom-dia', 'boa-noite', 'fechar'):
    assert (root / 'skills' / name / 'SKILL.md').is_file(), name
print('Plugin manifests and six skill entrypoints validated')
