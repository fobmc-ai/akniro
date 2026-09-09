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
for user_id, display_name, role in [('U-002', 'PLC 工程师', 'engineer'), ('U-003', '质量工程师', 'qa')]:
    try:
        store.create_user(user_id=user_id, tenant_id=project['tenant_id'], display_name=display_name, role=role)
    except Exception as exc:
        if 'UNIQUE' not in str(exc).upper():
            raise
    store.add_member(project_id=args.project, user_id=user_id, role=role)
samples = [
    ('DG-QUAL-001', 'design_goal', '每个功能先定义目标与验收标准', {'source': 'QUALITY_LIFECYCLE_SYSTEM.md', 'placeholder': False}),
    ('TC-QUAL-001', 'test_case', 'PM API/UI smoke test', {'steps': ['创建项目', '导入实施路线', '查询证据'], 'inputs': {'projectKind': 'platform'}, 'expected': {'traceable': True}, 'thresholds': {'maxErrors': 0}}),
    ('TV-PLC-001', 'tool_validation', 'PLC 工具链 Golden Project 验证（占位）', {'toolVersion': 'TBD', 'placeholder': True}),
    ('ART-PLC-001', 'artifact', 'PLC 工程资产索引（占位）', {'artifactType': 'PLC', 'contentHash': 'TBD', 'placeholder': True}),
    ('PAR-001', 'parameter_snapshot', '设备参数快照（占位）', {'source': 'edge-runtime', 'approvalRequired': True, 'placeholder': True}),
    ('KB-001', 'knowledge', '问题关闭必须有回归证据', {'verification': '待 QA 验证'}),
    ('REL-001', 'release', '织能控制中心 V0.1', {'rollback': '上一版本', 'evidenceRequired': True}),
    ('MNT-001', 'maintenance', '现场版本盘点（占位）', {'machineId': 'TBD', 'placeholder': True}),
    ('EV-001', 'evidence', 'PM-0 API/UI 验收证据', {'source': 'unittest', 'result': 'PASSED', 'contentHash': 'sha256:demo-evidence-0001'}),
]
for entity_id, entity_type, title, payload in samples:
    try:
        store.create_entity(entity_id=entity_id, entity_type=entity_type, project_id=args.project, tenant_id=project['tenant_id'], title=title, owner_id='U-001', payload=payload)
    except Exception as exc:
        if 'UNIQUE' not in str(exc).upper():
            raise
try:
    store.create_artifact_manifest(artifact_id='ART-DEMO-PLC', project_id=args.project, artifact_type='PLC', source_uri='local://demo/plc-project', content_hash='sha256:demo-plc-0001', artifact_revision='r1', toolchain_version='SIMULATED-0.1', target_environment='SIMULATION', sensitivity='INTERNAL', owner_id='U-001')
except Exception as exc:
    if 'UNIQUE' not in str(exc).upper():
        raise
machine_objects = [
    ('M-DEMO-001', 'machine', '演示自动化设备', None, {'model': 'DNA-v1'}),
    ('MOD-DEMO-PLC', 'module', 'PLC 控制模块', 'M-DEMO-001', {'domain': 'PLC'}),
    ('DEV-DEMO-PLC', 'device', 'PLC 控制器', 'MOD-DEMO-PLC', {'protocol': 'SIMULATED'}),
    ('TAG-DEMO-START', 'tag', 'StartCommand', 'DEV-DEMO-PLC', {'dataType': 'BOOL', 'access': 'READ_ONLY'}),
    ('ALM-DEMO-001', 'alarm', '安全门未闭合', 'M-DEMO-001', {'severity': 'S1'}),
    ('REC-DEMO-001', 'recipe', '默认配方', 'M-DEMO-001', {'version': '1.0'}),
]
for object_id, object_type, name, parent_id, payload in machine_objects:
    try:
        store.create_machine_object(object_id=object_id, project_id=args.project, tenant_id=project['tenant_id'], object_type=object_type, name=name, owner_id='U-001', parent_id=parent_id, payload=payload)
    except Exception as exc:
        if 'UNIQUE' not in str(exc).upper():
            raise
try:
    if not store.db.execute("SELECT 1 FROM machine_snapshots WHERE id = ?", ('SNAP-DEMO-001',)).fetchone():
        store.snapshot_machine(snapshot_id='SNAP-DEMO-001', project_id=args.project, machine_id='M-DEMO-001', created_by='U-001')
except Exception:
    pass
try:
    store.notify(notification_id='N-DEMO-001', project_id=args.project, recipient_id='U-001', kind='review', message='请检查演示工程 Release Gate')
except Exception:
    pass
try:
    store.enqueue_sync(sync_id='SYNC-DEMO-001', project_id=args.project, tenant_id=project['tenant_id'], direction='PULL_SNAPSHOT', object_type='artifact', object_id='ART-DEMO-PLC', idempotency_key='demo-sync-001', payload={'source': 'edge-demo'})
    store.transition_sync('SYNC-DEMO-001', 'CONFLICT', '演示 Hash 与项目 revision 不一致')
except Exception:
    pass
try:
    store.link_entities(project_id=args.project, from_id='REL-001', to_id='EV-001', link_type='requires')
except Exception:
    pass
try:
    evidence = store.get_entity('EV-001')
    if evidence['status'] == 'DRAFT':
        store.transition(entity_id='EV-001', target='VALIDATED', actor_id='U-001', expected_revision=evidence['revision'])
except Exception:
    pass
print({'inserted': inserted, 'total': len(store.list_backlog(args.project)), 'sampleEntities': len(samples)})
store.close()
