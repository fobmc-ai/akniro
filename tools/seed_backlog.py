import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))
from zhinen_pm.store import ProjectStore

parser = argparse.ArgumentParser()
parser.add_argument('--database', default='control-center-demo.db')
parser.add_argument('--project', default='DEMO-001')
args = parser.parse_args()
store = ProjectStore(args.database)
items = json.loads((Path(__file__).parents[1] / 'examples' / 'implementation-backlog.json').read_text(encoding='utf-8'))
inserted = store.import_backlog(project_id=args.project, items=items, actor_id='U-001')
project = store.get_project(args.project)
samples = [
    ('DG-QUAL-001', 'design_goal', '每个功能先定义目标与验收标准', {'source': 'QUALITY_LIFECYCLE_SYSTEM.md', 'placeholder': False}),
    ('TC-QUAL-001', 'test_case', 'PM API/UI smoke test', {'steps': ['创建项目', '导入实施路线', '查询证据'], 'expected': '可追溯'}),
    ('TV-PLC-001', 'tool_validation', 'PLC 工具链 Golden Project 验证（占位）', {'toolVersion': 'TBD', 'placeholder': True}),
    ('ART-PLC-001', 'artifact', 'PLC 工程资产索引（占位）', {'artifactType': 'PLC', 'contentHash': 'TBD', 'placeholder': True}),
    ('PAR-001', 'parameter_snapshot', '设备参数快照（占位）', {'source': 'edge-runtime', 'approvalRequired': True, 'placeholder': True}),
    ('KB-001', 'knowledge', '问题关闭必须有回归证据', {'verification': '待 QA 验证'}),
    ('REL-001', 'release', '织能控制中心 V0.1', {'rollback': '上一版本', 'evidenceRequired': True}),
    ('MNT-001', 'maintenance', '现场版本盘点（占位）', {'machineId': 'TBD', 'placeholder': True}),
]
for entity_id, entity_type, title, payload in samples:
    try:
        store.create_entity(entity_id=entity_id, entity_type=entity_type, project_id=args.project, tenant_id=project['tenant_id'], title=title, owner_id='U-001', payload=payload)
    except Exception as exc:
        if 'UNIQUE' not in str(exc).upper():
            raise
print({'inserted': inserted, 'total': len(store.list_backlog(args.project)), 'sampleEntities': len(samples)})
store.close()
