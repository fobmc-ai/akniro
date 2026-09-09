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
print({'inserted': store.import_backlog(project_id=args.project, items=items, actor_id='U-001'), 'total': len(store.list_backlog(args.project))})
store.close()
