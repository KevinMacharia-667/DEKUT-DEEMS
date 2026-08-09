import os
import glob
import re

css_files = glob.glob(r'c:\Users\ADMIN\Documents\SEM 4.1\PROJECT\antigravity iteration\frontend\src\**\*.css', recursive=True)

color_map = {
    '#0a0e17': 'var(--bg)',
    '#111827': 'var(--surface)',
    '#10b981': 'var(--primary)',
    '#34d399': 'var(--primary-tint)',
    '#059669': 'var(--primary-dark)',
    '#f59e0b': 'var(--accent-gold)',
    '#fbbf24': 'var(--accent-gold)',
    '#f3f4f6': 'var(--text)',
    '#9ca3af': 'var(--text-muted)',
    '#6b7280': 'var(--text-muted)',
    '#ef4444': 'var(--link-hover)',
    '#3b82f6': 'var(--primary-dark)',
    '#f87171': 'var(--link-hover)',
    '#cbd5e1': 'var(--border)',
    '#fff': '#FFFFFF', # we can replace #fff with var(--bg) or just leave it as #FFFFFF and let the CSS engine handle it, but wait, let's use var(--bg)
    '#ffffff': 'var(--bg)',
    '#334155': 'var(--text)',
    '#1e3a8a': 'var(--primary-dark)',
    '#64748b': 'var(--text-muted)',
    '#b91c1c': 'var(--link-hover)',
    '#475569': 'var(--text-muted)',
    '#eff6ff': 'var(--primary-tint)',
    '#bfdbfe': 'var(--border)',
    '#60a5fa': 'var(--primary-dark)'
}

for path in css_files:
    if 'index.css' in path:
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace #fff with var(--bg)
    content = re.sub(r'#fff(?!\w)', 'var(--bg)', content, flags=re.IGNORECASE)
    
    for old_color, new_var in color_map.items():
        if old_color == '#fff': continue
        pattern = re.compile(old_color + r'(?!\w)', re.IGNORECASE)
        content = pattern.sub(new_var, content)
        
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Updated all other CSS files.')
