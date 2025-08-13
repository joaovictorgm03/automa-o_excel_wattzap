 Automação de Envio de Mensagens no WhatsApp via Selenium

Este projeto permite **enviar mensagens automaticamente pelo WhatsApp Web** utilizando **Python + Selenium**,  
sem precisar apertar Enter manualmente.  
O script lê uma planilha (`.xlsx` ou `.csv`) com contatos e mensagens e faz o envio de forma **100% automatizada**.

---

 Funcionalidades
✅ Leitura de contatos de arquivos `.xlsx` ou `.csv`  
✅ Suporte a emojis e quebras de linha (`\n`)  
✅ Reuso da sessão do WhatsApp Web (login apenas uma vez)  
✅ Envio automático clicando no botão Enviar
✅ Delay configurável entre os envios  
✅ Geração de relatório CSV com status de cada mensagem (`OK` ou `FAIL`)  

---

 Requisitos
- Python 3.9+
- Google Chrome instalado
- Bibliotecas Python:
  ```bash
  pip install selenium webdriver-manager pandas openpyxl
