# Contribuindo

Este projeto segue um fluxo simples de engenharia: mudancas pequenas, testaveis e revisadas antes de entrar na branch principal.

## Regras basicas

- Rode `python manage.py check --fail-level WARNING` antes de abrir PR.
- Rode `python manage.py test` para validar regressao.
- Nao versione banco local, logs, arquivos de cobertura ou variaveis reais de ambiente.
- Prefira mudancas pequenas e focadas. Refatoracao sem relacao direta deve ir em outro PR.
- Views devem manter tratamento explicito para falha de backend, payload invalido e sessao ausente.
- Templates devem herdar `portal/base.html` e usar os estilos existentes antes de criar novas classes.
- Dados fake devem ficar claramente isolados em modo demo.

## Definition of Done

- Codigo executa localmente.
- Testes automatizados passam.
- Fluxo principal foi validado manualmente quando houver alteracao visual.
- README ou documentacao foram atualizados quando comandos, variaveis ou comportamento mudarem.
- CI passa no GitHub Actions.
