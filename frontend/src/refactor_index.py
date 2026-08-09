import os
import re

css_path = r'c:\Users\ADMIN\Documents\SEM 4.1\PROJECT\antigravity iteration\frontend\src\index.css'
with open(css_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace root variables entirely
new_root = """:root {
  --primary: #34B233;        /* vibrant green — fills, large elements */
  --primary-dark: #1E7A1E;   /* small-text buttons, green text links, hover */
  --primary-tint: #E9F9E7;   /* light green backgrounds, selected states */
  --accent-gold: #EAB308;    /* highlights: score badges, "NEW", logo */
  --link-hover: #C8102E;     /* red hover for hyperlinks (university-style) */
  --bg: #FFFFFF;
  --surface: #F7FAF7;
  --text: #0F172A;
  --text-muted: #64748B;
  --border: #D8E5D8;

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  /* Typography */
  --font-body: 'Inter', system-ui, -apple-system, sans-serif;
  --font-heading: 'Outfit', 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 250ms ease;
  --transition-slow: 400ms ease;
}"""

content = re.sub(r':root\s*\{.*?(?=/\* ── Reset)', new_root + '\n\n', content, flags=re.DOTALL)

# Refactor the styles
content = content.replace('var(--bg-primary)', 'var(--bg)')
content = content.replace('var(--bg-secondary)', 'var(--surface)')
content = content.replace('var(--bg-card)', 'var(--surface)')
content = content.replace('var(--bg-glass)', 'var(--surface)')
content = content.replace('var(--bg-input)', 'var(--surface)')
content = content.replace('var(--bg-input-focus)', 'var(--bg)')

content = content.replace('var(--accent)', 'var(--primary)')
content = content.replace('var(--accent-light)', 'var(--primary-tint)')
content = content.replace('var(--accent-dark)', 'var(--primary-dark)')
content = content.replace('var(--accent-bg)', 'var(--primary-tint)')
content = content.replace('var(--accent-bg-hover)', 'var(--primary-tint)')
content = content.replace('var(--accent-border)', 'var(--primary)')

content = content.replace('var(--gold)', 'var(--accent-gold)')
content = content.replace('var(--gold-light)', 'var(--accent-gold)')
content = content.replace('var(--gold-bg)', 'rgba(234, 179, 8, 0.1)')

content = content.replace('var(--text-primary)', 'var(--text)')
content = content.replace('var(--text-secondary)', 'var(--text-muted)')
content = content.replace('var(--text-inverse)', 'var(--bg)')
content = content.replace('color: var(--bg)', 'color: var(--text)')

content = content.replace('var(--border-light)', 'var(--border)')

content = content.replace('var(--success)', 'var(--primary)')
content = content.replace('var(--error)', 'var(--link-hover)')
content = content.replace('var(--warning)', 'var(--accent-gold)')
content = content.replace('var(--info)', 'var(--primary-dark)')

# Fix button colors and gradients (no gradients anywhere)
btn_primary = """.btn-primary {
  background: var(--primary);
  color: var(--text);
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}
.btn-primary:hover {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
  transform: translateY(-1px);
  color: #FFFFFF;
}"""
content = re.sub(r'\.btn-primary\s*\{.*?(?=\.btn-secondary)', btn_primary + '\n\n', content, flags=re.DOTALL)

# Fix links
a_links = """a {
  color: var(--primary-dark);
  text-decoration: none;
  transition: color var(--transition-fast);
}
a:hover {
  color: var(--link-hover);
  text-decoration: underline;
}"""
content = re.sub(r'a\s*\{.*?(?=\/\* ── Buttons)', a_links + '\n\n', content, flags=re.DOTALL)

# Remove body gradient background
content = re.sub(r'body::before\s*\{.*?(?=\#root)', '', content, flags=re.DOTALL)

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done index.css')
