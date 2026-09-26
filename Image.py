📂 O_Teu_Projeto/
 ┣ 📜 maquina_vending.py
 ┗ 📂 imagens/
   ┣ 🖼️ A1.jpg   (Foto da Coca-Cola)
   ┣ 🖼️ A2.jpg   (Foto da Água Mineral)
   ┣ 🖼️ A3.jpg   (Foto do Sprite)
   ┣ 🖼️ B1.jpg   (Foto das Batatas Fritas)
   ┣ 🖼️ B2.jpg   (Foto dos Chocolates)
   ┣ 🖼️ B3.jpg   (Foto do Energético)
   ┗ 🖼️ DESTINO.jpg (Foto do Botão do Destino)
import logging, re, time, json, csv, os, threading
import tkinter as tk
from tkinter import scrolledtext
from decimal import Decimal
from datetime import datetime
from PIL import Image, ImageTk  # Biblioteca para manipulação e redimensionamento das fotos

try: 
    import winsound
except ImportError: 
    winsound = None

class TkLog(logging.Handler):
    def __init__(self, tw): 
        super().__init__()
        self.tw = tw
    def emit(self, r): 
        m = self.format(r)
        self.tw.after(0, lambda: (self.tw.configure(state='normal'), self.tw.insert(tk.END, m+'\n'), self.tw.configure(state='disabled'), self.tw.yview(tk.END)))

logger = logging.getLogger("VM")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(message)s")

class VendingMachine:
    def __init__(self):
        self.saldo, self.jackpot, self.falhas, self.sf, self.cf, self.adm = Decimal("0.00"), Decimal("0.00"), 0, "vending_state.json", "vending_sales_log.csv", "SOYUZ1967"
        self.vouchers = {"DESCONTO10": Decimal("0.50"), "PROMOVIP": Decimal("1.00")}
        
        # O dicionário agora inclui os caminhos locais para as fotografias de cada item
        self.produtos = {
            "A1": {"nome": "Coca-Cola", "preco": Decimal("1.50"), "stock": 10, "imagem": "imagens/A1.jpg"}, 
            "A2": {"nome": "Água Mineral", "preco": Decimal("1.00"), "stock": 10, "imagem": "imagens/A2.jpg"},
            "A3": {"nome": "Sprite", "preco": Decimal("1.40"), "stock": 10, "imagem": "imagens/A3.jpg"}, 
            "B1": {"nome": "Batatas Fritas", "preco": Decimal("1.20"), "stock": 10, "imagem": "imagens/B1.jpg"},
            "B2": {"nome": "Chocolates", "preco": Decimal("1.80"), "stock": 10, "imagem": "imagens/B2.jpg"}, 
            "B3": {"nome": "Energético", "preco": Decimal("2.50"), "stock": 10, "imagem": "imagens/B3.jpg"},
            "DESTINO": {"nome": "Botão do Destino", "preco": Decimal("1.10"), "stock": 10, "imagem": "imagens/DESTINO.jpg"}
        }
        
        self.tubos = {Decimal("2.00"): 10, Decimal("1.00"): 10, Decimal("0.50"): 20, Decimal("0.20"): 20, Decimal("0.10"): 30, Decimal("0.05"): 40}
        
        if os.path.exists(self.sf):
            try:
                with open(self.sf, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    for k, v in d.get("produtos", {}).items():
                        if k in self.produtos: 
                            self.produtos[k]["stock"], self.produtos[k]["preco"] = int(v["stock"]), Decimal(str(v["preco"]))
                    for k, v in d.get("tubos", {}).items(): 
                        self.tubos[Decimal(k)] = int(v)
                logger.info("💾 [COFRE] Estado carregado com moedas atualizadas.")
            except Exception as e: 
                logger.error(f"⚠️ Erro JSON: {e}")

    def som(self, t="curto"):
        def _s():
            if winsound:
                if t == "curto": [winsound.Beep(f, 50) for f in range(1500, 2200, 150)]
                elif t == "quantico": [winsound.Beep(f, 40) for f in range(2000, 3000, 250)]
                elif t == "sabotagem": [winsound.Beep(800, 200) for _ in range(4)]
                else:
                    for _ in range(3):
                        [winsound.Beep(f, 35) for f in range(1400, 2600, 300)]
                        [winsound.Beep(f, 35) for f in range(2600, 1400, -300)]
        threading.Thread(target=_s, daemon=True).start()

    def salvar(self):
        try:
            d = {"produtos": {k: {"nome": v["nome"], "preco": str(v["preco"]), "stock": v["stock"]} for k, v in self.produtos.items()}, "tubos": {str(k): v for k, v in self.tubos.items()}}
            with open(self.sf, 'w', encoding='utf-8') as f: 
                json.dump(d, f, indent=4, ensure_ascii=False)
        except: 
            pass

    def log_csv(self, s, n, p, nif):
        ex = os.path.exists(self.cf)
        try:
            with open(self.cf, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if not ex: 
                    w.writerow(["Timestamp", "Slot", "Produto", "Preco", "NIF"])
                w.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s, n, f"{p:.2f}", nif])
        except: 
            pass

    def calc_troco(self, val: Decimal) -> dict:
        res, resto = {}, val
        for m in sorted(self.tubos.keys(), reverse=True):
            if resto <= 0: break
            q = min(int(resto // m), self.tubos[m])
            if q > 0: 
                res[m] = q
                resto -= m * q
        return res if resto == 0 else None

    def atualizar_bolsa(self, slot):
        if slot == "DESTINO": return
        for s, p in self.produtos.items():
            if s == "DESTINO": continue
            p["preco"] = max(Decimal("0.50"), p["preco"] + Decimal("0.10")) if s == slot else max(Decimal("0.40"), p["preco"] - Decimal("0.05"))
        self.salvar()

    def inserir_moeda(self, v: Decimal):
        if v in self.tubos:
            self.tubos[v] += 1
            self.saldo += v
            self.som("curto")
            logger.info(f"🪙 Moeda {v:.2f}€. Saldo: {self.saldo:.2f}€")
            self.salvar()
            return True
        logger.error(f"❌ Moeda de {v:.2f}€ rejeitada.")
        return False

    def devolver_saldo(self):
        if self.saldo <= 0: return {}
        tr = self.calc_troco(self.saldo)
        if tr:
            for m, q in tr.items(): 
                self.tubos[m] -= q
            logger.info(f"💰 Devolvido {self.saldo:.2f}€.")
            self.saldo = Decimal("0.00")
            self.salvar()
            self.som("curto")
            return tr
        return None

    def aplicar_voucher(self, c: str):
        if c in self.vouchers: 
            d = self.vouchers[c]
            self.saldo += d
            del self.vouchers[c]
            logger.info(f"🎟️ Voucher {c} (+{d:.2f}€)")
            self.som("quantico")
            return True
        return False

    def comprar_produto(self, s: str, nif: str = "999999999") -> bool:
        if s not in self.produtos: return False
        p = self.produtos[s]
        if p["stock"] <= 0 or self.saldo < p["preco"]: return False
        exc = self.saldo - p["preco"]
        tr = self.calc_troco(exc)
        if exc > 0 and tr is None: return False
        
        p["stock"] -= 1
        if exc > 0:
            for m, q in tr.items(): 
                self.tubos[m] -= q
        if s != "DESTINO": 
            self.jackpot += p["preco"] * Decimal("0.05")
            
        logger.info(f"✅ {p['nome']} dispensado! Troco: {exc:.2f}€")
        self.log_csv(s, p["nome"], p["preco"], nif)
        self.saldo = Decimal("0.00")
        self.som("quantico" if s == "DESTINO" else "longo")
        self.atualizar_bolsa(s)
        self.salvar()
        return True

    def autenticar_admin(self, c: str) -> bool:
        if c == self.adm: 
            self.falhas = 0
            logger.info("🛠️ Admin OK.")
            return True
        self.falhas += 1
        if self.falhas >= 3: 
            self.som("sabotagem")
            logger.critical("🚨 Alerta Invasão!")
        return False

class VMUi:
    def __init__(self, vm):
        self.vm, self.u_clique = vm, 0.0
        self.root = tk.Tk()
        self.root.title("Soyuz Bird - Vending System")
        self.root.geometry("540x900") # Aumentado ligeiramente o tamanho da janela para as imagens
        self.root.configure(bg="#121214")
        
        # Dicionário interno para segurar referências a imagens ativas na memória (evita garbage collection do Python)
        self.imagens_tk = {}

        # Log de Monitorização superior
        self.txt = scrolledtext.ScrolledText(self.root, height=8, bg="#0d0e15", fg="#a9b7c6", font=("Courier", 9), state='disabled')
        self.txt.pack(pady=5, fill="x", padx=15)
        th = TkLog(self.txt)
        th.setFormatter(fmt)
        logger.addHandler(th)
        
        # Display de Saldo Corrente
        self.lbl_saldo = tk.Label(self.root, text="0.00€", font=("Courier", 22, "bold"), fg="#00ff00", bg="#000000", height=2)
        self.lbl_saldo.pack(pady=5, fill="x", padx=15)
        
        # Canvas Operacional
        self.cv = tk.Canvas(self.root, width=400, height=60, bg="#0a0f1d", highlightthickness=1, highlightbackground="#00ff00")
        self.cv.pack(pady=5, padx=15, fill="x")
        self.lbl_pique = self.cv.create_text(250, 30, text="📊 SISTEMA OPERACIONAL\nInsira moedas ou introduza código", fill="#00ff00", font=("Arial", 10, "bold"), justify="center")
        
        # Área de Input de Tokens / NIF
        f_nif = tk.LabelFrame(self.root, text=" Cliente / Admin ", fg="white", bg="#121214")
        f_nif.pack(pady=5, fill="x", padx=15)
        tk.Label(f_nif, text="CÓDIGO/NIF:", fg="white", bg="#121214").pack(side="left", padx=5)
        self.ent_nif = tk.Entry(f_nif, width=15)
        self.ent_nif.pack(side="left", padx=5, pady=5)
        tk.Button(f_nif, text="🔑 Validar", bg="#333", fg="white", command=self.validar).pack(side="left", padx=5)
        tk.Button(f_nif, text="🪙 Devolver", bg="#c62828", fg="white", command=self.devolver).pack(side="right", padx=5)

        # Contentor Dinâmico de Produtos com Imagens
        self.f_produtos = tk.LabelFrame(self.root, text=" Produtos Disponíveis (Clique para Comprar) ", fg="#00ffff", bg="#121214")
        self.f_produtos.pack(pady=5, fill="both", expand=True, padx=15)
        
        # Renderização da Vitrine Digital
        self.renderizar_produtos()

        # Interface Financeira Automática (Moedas Aceites)
        fm = tk.LabelFrame(self.root, text=" Ranhura de Moedas ", fg="white", bg="#121214")
        fm.pack(pady=5, fill="x", padx=15)
        
        for m in sorted(self.vm.tubos.keys()):
            btn = tk.Button(fm, text=f"{m:.2f}€", bg="#2a2a30", fg="#00ff00", font=("Arial", 9, "bold"),
                            command=lambda valor=m: self.inserir_moeda(valor))


import logging, re, time, json, csv, os, threading
from decimal import Decimal; from datetime import datetime

logger = logging.getLogger("VM"); logger.setLevel(logging.INFO)

class VendingMachine:
    def __init__(self):
        self.saldo, self.jackpot, self.falhas, self.sf, self.cf, self.adm = Decimal("0.00"), Decimal("0.00"), 0, "vending_state.json", "vending_sales_log.csv", "SOYUZ1967"
        self.vouchers = {"DESCONTO10": Decimal("0.50"), "PROMOVIP": Decimal("1.00")}
        self.produtos = {
            "A1": {"nome": "Coca-Cola", "preco": Decimal("1.50"), "stock": 10, "imagem": "imagens/A1.jpg"}, 
            "A2": {"nome": "Água Mineral", "preco": Decimal("1.00"), "stock": 10, "imagem": "imagens/A2.jpg"},
            "A3": {"nome": "Sprite", "preco": Decimal("1.40"), "stock": 10, "imagem": "imagens/A3.jpg"}, 
            "B1": {"nome": "Batatas Fritas", "preco": Decimal("1.20"), "stock": 10, "imagem": "imagens/B1.jpg"},
            "B2": {"nome": "Chocolates", "preco": Decimal("1.80"), "stock": 10, "imagem": "imagens/B2.jpg"}, 
            "B3": {"nome": "Energético", "preco": Decimal("2.50"), "stock": 10, "imagem": "imagens/B3.jpg"},
            "DESTINO": {"nome": "Botão do Destino", "preco": Decimal("1.10"), "stock": 10, "imagem": "imagens/DESTINO.jpg"}
        }
        self.tubos = {Decimal("2.00"): 10, Decimal("1.00"): 10, Decimal("0.50"): 20, Decimal("0.20"): 20, Decimal("0.10"): 30, Decimal("0.05"): 40}
        self.carregar_estado()

    def carregar_estado(self):
        if os.path.exists(self.sf):
            try:
                with open(self.sf, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    for k, v in d.get("produtos", {}).items():
                        if k in self.produtos: self.produtos[k]["stock"], self.produtos[k]["preco"] = int(v["stock"]), Decimal(str(v["preco"]))
                    for k, v in d.get("tubos", {}).items(): self.tubos[Decimal(k)] = int(v)
                logger.info("💾 Estado do cofre carregado.")
            except Exception as e: logger.error(f"⚠️ Erro JSON: {e}")

    def som(self, t="curto"):
        def _s():
            try:
                import winsound
                if t == "curto": [winsound.Beep(f, 50) for f in range(1500, 2200, 150)]
                elif t == "quantico": [winsound.Beep(f, 40) for f in range(2000, 3000, 250)]
                elif t == "sabotagem": [winsound.Beep(800, 200) for _ in range(4)]
                else:
                    for _ in range(3): [winsound.Beep(f, 35) for f in range(1400, 2600, 300)]; [winsound.Beep(f, 35) for f in range(2600, 1400, -300)]
            except: pass
        threading.Thread(target=_s, daemon=True).start()

    def salvar(self):
        try:
            d = {"produtos": {k: {"nome": v["nome"], "preco": str(v["preco"]), "stock": v["stock"]} for k, v in self.produtos.items()}, "tubos": {str(k): v for k, v in self.tubos.items()}}
            with open(self.sf, 'w', encoding='utf-8') as f: json.dump(d, f, indent=4, ensure_ascii=False)
        except: pass

    def log_csv(self, s, n, p, nif):
        ex = os.path.exists(self.cf)
        try:
            with open(self.cf, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                if not ex: w.writerow(["Timestamp", "Slot", "Produto", "Preco", "NIF"])
                w.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s, n, f"{p:.2f}", nif])
        except: pass

    def calc_troco(self, val: Decimal) -> dict:
        res, resto = {}, val
        for m in sorted(self.tubos.keys(), reverse=True):
            if resto <= 0: break
            q = min(int(resto // m), self.tubos[m])
            if q > 0: res[m] = q; resto -= m * q
        return res if resto == 0 else None

    def atualizar_bolsa(self, slot):
        if slot == "DESTINO": return
        for s, p in self.produtos.items():
            if s == "DESTINO": continue
            p["preco"] = max(Decimal("0.50"), p["preco"] + Decimal("0.10")) if s == slot else max(Decimal("0.40"), p["preco"] - Decimal("0.05"))
        self.salvar()

    def inserir_moeda(self, v: Decimal):
        if v in self.tubos:
            self.tubos[v] += 1; self.saldo += v; self.som("curto")
            logger.info(f"🪙 Moeda {v:.2f}€. Saldo: {self.saldo:.2f}€"); self.salvar(); return True
        logger.error(f"❌ Moeda rejeitada."); return False

    def devolver_saldo(self):
        if self.saldo <= 0: return {}
        tr = self.calc_troco(self.saldo)
        if tr:
            for m, q in tr.items(): self.tubos[m] -= q
            logger.info(f"💰 Devolvido {self.saldo:.2f}€."); self.saldo = Decimal("0.00"); self.salvar(); self.som("curto"); return tr
        return None

    def aplicar_voucher(self, c: str):
        if c in self.vouchers:
            d = self.vouchers[c]; self.saldo += d; del self.vouchers[c]
            logger.info(f"🎟️ Voucher {c} (+{d:.2f}€)"); self.som("quantico"); return True
        return False

    def comprar_produto(self, s: str, nif: str) -> bool:
        if s not in self.produtos: return False
        p = self.produtos[s]
        if p["stock"] <= 0 or self.saldo < p["preco"]: return False
        exc = self.saldo - p["preco"]; tr = self.calc_troco(exc)
        if exc > 0 and tr is None: return False
        p["stock"] -= 1
        if exc > 0:
            for m, q in tr.items(): self.tubos[m] -= q
        if s != "DESTINO": self.jackpot += p["preco"] * Decimal("0.05")
        logger.info(f"✅ {p['nome']}! Troco: {exc:.2f}€"); self.log_csv(s, p["nome"], p["preco"], nif); self.saldo = Decimal("0.00")
        self.som("quantico" if s == "DESTINO" else "longo"); self.atualizar_bolsa(s); self.salvar(); return True

    def autenticar_admin(self, c: str) -> bool:
        if c == self.adm: self.falhas = 0; logger.info("🛠️ Admin OK."); return True
        self.falhas += 1
        if self.falhas >= 3: self.som("sabotagem"); logger.critical("🚨 Alerta Invasão!")
        return False
             import tkinter as tk
import os, time, re, logging
from tkinter import scrolledtext; from decimal import Decimal
from PIL import Image, ImageTk
from maquina import VendingMachine, logger, fmt

class TkLog(logging.Handler):
    def __init__(self, tw): super().__init__(); self.tw = tw
    def emit(self, r): m = self.format(r); self.tw.after(0, lambda: (self.tw.configure(state='normal'), self.tw.insert(tk.END, m+'\n'), self.tw.configure(state='disabled'), self.tw.yview(tk.END)))

class VMUi:
    def __init__(self, vm):
        self.vm, self.u_clique = vm, 0.0; self.root = tk.Tk(); self.root.title("Soyuz Bird"); self.root.geometry("540x920"); self.root.configure(bg="#121214"); self.imagens_tk = {}
        self.txt = scrolledtext.ScrolledText(self.root, height=8, bg="#0d0e15", fg="#a9b7c6", font=("Courier", 9), state='disabled'); self.txt.pack(pady=5, fill="x", padx=15)
        th = TkLog(self.txt); th.setFormatter(fmt); logger.addHandler(th)
        self.lbl_saldo = tk.Label(self.root, text="0.00€", font=("Courier", 22, "bold"), fg="#00ff00", bg="#000000", height=2); self.lbl_saldo.pack(pady=5, fill="x", padx=15)
        self.cv = tk.Canvas(self.root, width=400, height=60, bg="#0a0f1d", highlightthickness=1, highlightbackground="#00ff00"); self.cv.pack(pady=5, padx=15, fill="x")
        self.lbl_pique = self.cv.create_text(250, 30, text="📊 SISTEMA OPERACIONAL\nInsira moedas ou use MB WAY", fill="#00ff00", font=("Arial", 10, "bold"), justify="center")
        
        f_nif = tk.LabelFrame(self.root, text=" Cliente / Admin ", fg="white", bg="#121214"); f_nif.pack(pady=2, fill="x", padx=15)
        tk.Label(f_nif, text="CÓDIGO:", fg="white", bg="#121214").pack(side="left", padx=5)
        self.ent_nif = tk.Entry(f_nif, width=15); self.ent_nif.pack(side="left", padx=5, pady=5)
        tk.Button(f_nif, text="🔑 Validar", bg="#333", fg="white", command=self.validar).pack(side="left", padx=5)
        tk.Button(f_nif, text="🪙 Devolver", bg="#c62828", fg="white", command=self.devolver).pack(side="right", padx=5)
        
        f_mb = tk.LabelFrame(self.root, text=" MB WAY ", fg="#00ffff", bg="#121214"); f_mb.pack(pady=2, fill="x", padx=15)
        tk.Button(f_mb, text="📲 Pagar com MB WAY (2.50€)", bg="#e83e8c", fg="white", font=("Arial", 9, "bold"), command=self.simular_mbway).pack(fill="x", pady=4, padx=5)
        
        self.f_produtos = tk.LabelFrame(self.root, text=" Produtos Disponíveis ", fg="#00ffff", bg="#121214"); self.f_produtos.pack(pady=5, fill="both", expand=True, padx=15)
        self.renderizar_produtos()
        
        fm = tk.LabelFrame(self.root, text=" Moedas Aceites ", fg="white", bg="#121214"); fm.pack(pady=5, fill="x", padx=15)
        for m in sorted(self.vm.tubos.keys()): 
            tk.Button(fm, text=f"{m:.2f}€", bg="#2a2a30", fg="#00ff00", font=("Arial", 9, "bold"), command=lambda valor=m: self.inserir_moeda(valor)).pack(side="left", fill="x", expand=True, padx=2, pady=5)
        self.atualizar_interface(); self.root.mainloop()

    def carregar_imagem_produto(self, slot, caminho_img):
        tamanho = (70, 70)
        if os.path.exists(caminho_img):
            try:
                img = Image.open(caminho_img); img = img.resize(tamanho, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as e: logger.error(f"Erro na imagem {caminho_img}: {e}")
        return ImageTk.PhotoImage(Image.new('RGB', tamanho, color='#3a3a42'))

    def renderizar_produtos(self):
        for widget in self.f_produtos.winfo_children(): widget.destroy()
        colunas = 3
        for i, (slot, dados) in enumerate(self.vm.produtos.items()):
            linha, col = i // colunas, i % colunas
            card = tk.Frame(self.f_produtos, bg="#1a1a1e", bd=2, relief="groove"); card.grid(row=linha, column=col, padx=8, pady=6, sticky="nsew"); self.f_produtos.grid_columnconfigure(col, weight=1)
            img_tk = self.carregar_imagem_produto(slot, dados["imagem"]); self.imagens_tk[slot] = img_tk 
            lbl_foto = tk.Label(card, image=img_tk, bg="#1a1a1e"); lbl_foto.pack(pady=4)
            lbl_info = tk.Label(card, text=f"[{slot}]\n{dados['nome']}\n{dados['preco']:.2f}€\nStock: {dados['stock']}", font=("Arial", 9), fg="white", bg="#1a1a1e", justify="center"); lbl_info.pack(pady=2)
            for w in (card, lbl_foto, lbl_info): w.bind("<Button-1>", lambda e, s=slot: self.comprar(s))

    def inserir_moeda(self, valor): self.vm.inserir_moeda(valor); self.atualizar_interface()
    def devolver(self): self.vm.devolver_saldo(); self.atualizar_interface()
    def simular_mbway(self): self.vm.saldo += Decimal("2.50"); logger.info("📲 MB WAY: Recebido 2.50€."); self.vm.som("quantico"); self.atualizar_interface()
    def atualizar_interface(self): self.lbl_saldo.config(text=f"{self.vm.saldo:.2f}€")
    
    def validar(self):
        c = self.ent_nif.get().strip()
        if c and (self.vm.aplicar_voucher(c) or self.vm.autenticar_admin(c)): self.ent_nif.delete(0, tk.END)
        self.atualizar_interface()

    def comprar(self, slot):
        agora = time.time()
        if agora - self.u_clique < 0.4: return
        self.u_clique = agora
        nif_input = self.ent_nif.get().strip(); nif = nif_input if re.match(r"^\d{9}$", nif_input) else "999999999"
        p = self.vm.produtos[slot]
        if p["stock"] <= 0: logger.error(f"❌ {p['nome']} esgotado!"); return
        if self.vm.saldo < p["preco"]: logger.error(f"❌ Saldo insuficiente."); return
        if self.vm.comprar_produto(slot, nif):
            if nif_input == nif: self.ent_nif.delete(0, tk.END)
            self.renderizar_produtos(); self.atualizar_interface()
        else: logger.error("❌ Sem moedas suficientes nos tubos para troco.")

if __name__ == "__main__":
    maquina = VendingMachine(); app = VMUi(maquina)

