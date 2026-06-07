#!/usr/bin/env python3
"""
Uplift Hu Clan tree data: assign unique IDs, infer parent links, metadata stubs.
Reads each data/<CODE>.json, enhances persons, writes back.
"""
import json, os, re, sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

BRANCHES = {
    'WX': {'id':'weixian','label':'维显公','color':'#7c3aed'},
    'WD': {'id':'weida','label':'维达公','color':'#dc2626'},
    'WF': {'id':'weifu','label':'维富公','color':'#ea580c'},
    'WH': {'id':'weihao','label':'维豪公','color':'#d97706'},
    'WY': {'id':'weiyuan','label':'维源公','color':'#16a34a'},
    'WU': {'id':'weiyou','label':'维有公','color':'#0d9488'},
    'QH': {'id':'qinghe','label':'清和公','color':'#2563eb'},
    'WZ': {'id':'wangzhong','label':'旺忠公','color':'#4f46e5'},
    'SH': {'id':'souhe','label':'叟和公','color':'#db2777'},
}

def make_pid(code, seq):
    return f'{code}_{seq:03d}'

def find_males(persons):
    """Find persons who are likely male parents."""
    return [p for p in persons if p.get('rel') in ('祖','兒','婿')]

def find_females(persons):
    """Find persons who are likely female parents."""
    return [p for p in persons if p.get('rel') in ('妻','媳','女')]

class IDCounter:
    def __init__(self):
        self.counters = {c: 0 for c in BRANCHES}

    def next(self, code):
        self.counters[code] += 1
        return make_pid(code, self.counters[code])

def walk_assign_ids(node, code, counter, parent_males, parent_females):
    """Recursively assign IDs and parent links."""
    if not node:
        return

    persons = node.get('persons', [])

    # Assign IDs to all persons in this node
    current_males = []
    current_females = []

    for p in persons:
        p['id'] = counter.next(code)
        # Set defaults
        p.setdefault('birth', None)
        p.setdefault('death', None)
        p.setdefault('notes', None)

        # Infer parent links from the PARENT node's males/females
        if parent_males:
            p['father_id'] = parent_males[0]['id']
        else:
            p['father_id'] = None

        if parent_females:
            # If multiple females, we can't determine which is the mother
            if len(parent_females) == 1:
                p['mother_id'] = parent_females[0]['id']
            else:
                p['mother_id'] = None
                p['unknown_mother'] = True
        else:
            p['mother_id'] = None

        # Track males/females in THIS node for children
        if p.get('rel') in ('祖','兒','婿'):
            current_males.append(p)
        if p.get('rel') in ('妻','媳','女'):
            current_females.append(p)

    # If no clear male in this node, use parent's males
    if not current_males:
        current_males = parent_males
    # If no clear female in this node, use parent's females
    if not current_females:
        current_females = parent_females

    # Recurse into children
    for child in node.get('children', []):
        walk_assign_ids(child, code, counter, current_males, current_females)

def main():
    for code in sorted(BRANCHES.keys()):
        filepath = os.path.join(DATA_DIR, f'{code}.json')
        if not os.path.exists(filepath):
            print(f'  SKIP {code}: file not found')
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Add version and metadata
        data.setdefault('_meta', {})
        data['_meta']['version'] = 2
        data['_meta']['schema'] = 'person-centric'
        data['_meta']['description'] = (
            'Each person has a unique ID. father_id/mother_id link to parent IDs. '
            'unknown_mother=true when mother cannot be determined from data. '
            'Add birth, death, notes as needed.'
        )

        counter = IDCounter()
        walk_assign_ids(data.get('root'), code, counter, [], [])

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Count persons
        def count_persons(node):
            if not node: return 0
            c = len(node.get('persons', []))
            for child in node.get('children', []):
                c += count_persons(child)
            return c

        total = count_persons(data.get('root'))
        print(f'  {code}: {total} persons with IDs ({counter.counters[code]} total), v2')

    # Also update the combined file
    combined_path = os.path.join(DATA_DIR, 'tree-data.json')
    if os.path.exists(combined_path):
        with open(combined_path, 'r', encoding='utf-8') as f:
            combined = json.load(f)
        for entry in combined:
            code = entry.get('code')
            branch_file = os.path.join(DATA_DIR, f'{code}.json')
            if os.path.exists(branch_file):
                with open(branch_file, 'r', encoding='utf-8') as f:
                    updated = json.load(f)
                    entry['root'] = updated['root']
                    entry['_meta'] = updated.get('_meta', {})
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f'  Combined tree-data.json updated')

    print('Done.')

if __name__ == '__main__':
    main()
