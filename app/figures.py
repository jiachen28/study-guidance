"""Standalone, dependency-free SVG figures for the methods/results section."""
from html import escape
from pathlib import Path
from .policy import LABELS
BLUE = '#255b95'
GREY = '#e4eaf3'
INK = '#20354e'
MUTED = '#627a93'
TEAL = '#258b7b'

def svg_start(w, h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="white"/>'

def rect(x, y, w, h, fill, r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="{r}"/>'

def text(x, y, s, size=14, fill=INK, anchor='start', weight=400):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(s))}</text>'

def comparison(metrics, destination):
    methods = [('Keyword baseline', 'baseline'), ('Local language model', 'ollama'), ('Final guidance system', 'system')]
    out = [svg_start(770, 370), text(35, 40, 'Held-out classification performance', 21, weight=700), text(35, 63, 'N = 20; invalid model predictions are counted as incorrect', 12, MUTED)]
    for j, (title, key) in enumerate(methods):
        y = 98 + j * 82
        v = metrics[key]
        out.extend([text(35, y + 7, title, 15, INK, weight=600), rect(35, y + 20, 585, 18, GREY, 6), rect(35, y + 20, 585 * v['accuracy'], 18, BLUE if key != 'system' else TEAL, 6), text(640, y + 35, f"{100 * v['accuracy']:.1f}% accuracy", 13, INK)])
        out.append(text(35, y + 56, f"Macro F1 {v['macro_f1']:.3f}   |   Coverage {100 * v['coverage']:.0f}%", 11, MUTED))
    out.append('</svg>')
    Path(destination).write_text(''.join(out), encoding='utf-8')

def confusion(metrics, destination, method):
    cells = [*LABELS, 'Unavailable']
    m = metrics[method]['confusion']
    w = 780
    h = 470
    out = [svg_start(w, h), text(40, 42, f'Confusion matrix — {method}', 21, weight=700), text(40, 66, 'Rows: human reference labels  ·  Columns: predicted labels', 12, MUTED)]
    x0 = 170
    y0 = 147
    cw = 112
    ch = 65
    for j, pred in enumerate(cells):
        out.append(text(x0 + j * cw + cw / 2, 122, pred, 12, INK, 'middle', 600))
    for i, gold in enumerate(LABELS):
        out.append(text(x0 - 18, y0 + i * ch + 37, gold, 13, INK, 'end', 600))
        for j, pred in enumerate(cells):
            n = m[gold][pred]
            shade = '#dcebf7' if n > 0 else '#f4f7fb'
            if gold == pred and n > 0:
                shade = '#c7e9df'
            out.extend([rect(x0 + j * cw + 2, y0 + i * ch + 2, cw - 4, ch - 4, shade, 5), text(x0 + j * cw + cw / 2, y0 + i * ch + 40, n, 18, INK, 'middle', 600)])
    out.append('</svg>')
    Path(destination).write_text(''.join(out), encoding='utf-8')

def per_class(metrics, destination):
    out = [svg_start(780, 410), text(35, 40, 'Per-class F1 comparison', 21, weight=700), text(35, 65, 'Computed from the human-consensus reference labels', 12, MUTED)]
    for i, lab in enumerate(LABELS):
        y = 105 + i * 73
        out.extend([text(35, y + 14, lab, 13, INK, weight=600), rect(140, y, 520, 14, GREY, 5), rect(140, y, 520 * metrics['baseline']['by_class'][lab]['f1'], 14, BLUE, 5), rect(140, y + 21, 520, 14, GREY, 5), rect(140, y + 21, 520 * metrics['system']['by_class'][lab]['f1'], 14, TEAL, 5)])
    out.extend([rect(35, 393, 12, 8, BLUE), text(52, 401, 'Keyword baseline', 11, MUTED), rect(215, 393, 12, 8, TEAL), text(232, 401, 'Final system', 11, MUTED), '</svg>'])
    Path(destination).write_text(''.join(out), encoding='utf-8')
