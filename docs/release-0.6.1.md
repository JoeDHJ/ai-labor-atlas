# AI Labor Atlas 0.6.1

Fix UTF-8 text encoding in the research interface and briefs, including navigation
symbols, title punctuation and newly edited text. Add a regression check for all
packaged text resources and broken interface symbols. The public datasets,
measurement calculations and organization-model equations are unchanged.

The complete 0.6 research workbench includes 758 comparable SOC occupations,
an offline SQL warehouse, a held-out silver-label task-text benchmark, six
hypothetical organization alternatives and an interview evidence guide.

Use 0.6.1 for the corrected interface:

```powershell
python -m pip install ai-labor-atlas==0.6.1
atlas workbench --output my-research
```

Live case: https://joedhj.github.io/ai-labor-atlas/
