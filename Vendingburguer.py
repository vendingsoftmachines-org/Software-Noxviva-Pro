
import logging
import json
import csv
import os
import threading
import tkinter as tk
from tkinter import scrolledtext
from decimal import Decimal
from datetime import datetime

class TkLog(logging.Handler):
    def __init__(self, tw):
        super().__init__()
        self.tw = tw

    def emit(self, r):
        m = self.format(r)
        def _update():
            self.tw.configure(state='normal')
            self.tw.insert(tk.END, m + '\n')
            self.tw.configure(state='disabled')
            self.tw.yview(tk.END)
        self.tw.after(0, _update)

logger = logging.getLogger("VM")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(message)s")

class VendingMachine:
    def __init__(self):
        self.saldo = Decimal("0.00")
        self.jackpot = Decimal("0.00")
        self.falhas = 0
        self.sf = "vending_state.json"
        self.cf = "vending_sales_log.csv"
        self.adm = "SOYUZ1967"
        self.vouchers = {"DESCONTO10": Decimal("0.50"), "PROMOVIP": Decimal("1.00")}
        self.produtos = {
            "A1": {"nome": "Coca-Cola", "preco": Decimal("1.50"), "stock": 10},
            "A2": {"nome": "Agua Mineral", "preco": Decimal("1.00"), "stock": 10},
            "A3": {"nome": "Sprite", "preco": Decimal("1.40"), "stock": 10},
            "B1": {"nome": "Batatas Fritas", "preco": Decimal("1.20"), "stock": 10},
            "B2": {"nome": "Chocolates", "preco": Decimal("1.80"), "stock": 10},
            "B3": {"nome": "Energetico", "preco": Decimal("2.50"), "stock": 10},
            "DESTINO": {"nome": "Botao do Destino", "preco": Decimal("1.10"), "stock": 10}
        }
        self.tubos = {
            Decimal("2.00"): 10,
            Decimal("1.00"): 10,
            Decimal("0.50"): 20,
            Decimal("0.20"): 20,
            Decimal("0.10"): 30,
            Decimal("0.05"): 40
        }

    def salvar(self):
        pass

    def log_csv(self, s, n, p, nif):
        pass

    def calc_troco(self, val: Decimal) -> dict:
        res = {}
        resto = val
        for m in sorted(self.tubos.keys(), reverse=True):
            if resto <= 0:
                break
            q = min(int(resto // m), self.tubos[m])
            if q > 0:
                res[m] = q
                resto -= m * q
        return res if resto == 0 else None

    def atualizar_bolsa(self, slot):
        if slot == "DESTINO":
            return
        for s, p in self.produtos.items():
            if s != "DESTINO":
                if s == slot:
                    p["preco"] = max(Decimal("0.50"), p["preco"] + Decimal("0.10"))
                else:
                    p["preco"] = max(Decimal("0.40"), p["preco"] - Decimal("0.05"))

    def inserir_moeda(self, v: Decimal):
        if v in self.tubos:
            self.tubos[v] += 1
            self.saldo += v
            logger.info(f"Saldo: {self.saldo:.2f} EUR")
            return True
        return False

    def devolver_saldo(self):
        tr = self.calc_troco(self.saldo) if self.saldo > 0 else None
        if tr:
            for m, q in tr.items():
                self.tubos[m] -= q
            logger.info(f"Devolvido {self.saldo:.2f} EUR.")
            self.saldo = Decimal("0.00")

    def aplicar_voucher(self, c: str):
        if c in self.vouchers:
            d = self.vouchers[c]
            self.saldo += d
            del self.vouchers[c]
            logger.info(f"Voucher ativo (+{d:.2f} EUR)")
            return True
        return False

    def comprar_produto(self, s: str, nif: str = "999999999") -> bool:
        if s not in self.produtos:
            return False
        p = self.produtos[s]
        if p["stock"] <= 0 or self.saldo < p["preco"]:
            return False
        exc = self.saldo - p["preco"]
        tr = self.calc_troco(exc)
        if exc > 0 and tr is None:
            return False
        p["stock"] -= 1
        if exc > 0:
            for m, q in tr.items():
                self.tubos[m] -= q
        logger.info(f"COMPRA: {p['nome']}! Troco: {exc:.2f} EUR")
        self.saldo = Decimal("0.00")
        self.atualizar_bolsa(s)
        return True

    def autenticar_admin(self, c: str) -> bool:
        if c == self.adm:
            logger.info("Admin Acedido.")
            return True
        self.falhas += 1
        return False

class VMUi:
    def __init__(self, vm):
        self.vm = vm
        self.root = tk.Tk()
        self.root.title("Soyuz Bird")
        self.root.geometry("460x820")
        self.root.configure(bg="#121214")
        
        self.txt = scrolledtext.ScrolledText(self.root, height=8, bg="#0d0e15", fg="#a9b7c6", font=("Courier", 8), state='disabled')
        self.txt.pack(pady=5, fill="both", expand=True, padx=15)
        
        th = TkLog(self.txt)
        th.setFormatter(fmt)
        logger.addHandler(th)
        
        self.lbl_saldo = tk.Label(self.root, text="0.00 EUR", font=("Courier", 20, "bold"), fg="#00ff00", bg="#000000", height=2)
        self.lbl_saldo.pack(pady=5, fill="x", padx=15)
        
        f_nif = tk.LabelFrame(self.root, text=" Codigo / Voucher ", fg="white", bg="#121214")
        f_nif.pack(pady=2, fill="x", padx=15)
        
        self.ent_nif = tk.Entry(f_nif, width=15)
        self.ent_nif.pack(side="left", padx=5, pady=5)
        
        tk.Button(f_nif, text="Validar", command=self.validar).pack(side="left", padx=5)
        
        f_mb = tk.LabelFrame(self.root, text=" MB WAY ", fg="#00ffff", bg="#121214")
        f_mb.pack(pady=2, fill="x", padx=15)
        
        tk.Button(f_mb, text="MB WAY (2.50 EUR)", bg="#e83e8c", fg="white", command=self.simular_mbway).pack(fill="x", pady=5, padx=5)
        
        fm = tk.LabelFrame(self.root, text=" Moedas ", fg="white", bg="#121214")
        fm.pack(pady=2, fill="x", padx=15)
        
        for m in sorted(self.vm.tubos.keys(), reverse=True):
            def make_cmd(moeda=m):
                return lambda: (self.vm.inserir_moeda(moeda), self.atualizar_ecra())
            tk.Button(fm, text=f"{m:.2f} EUR", command=make_cmd()).pack(side="left", expand=True, fill="x", padx=2, pady=5)
            
        fp = tk.LabelFrame(self.root, text=" Produtos ", fg="white", bg="#121214")
        fp.pack(pady=5, fill="both", expand=True, padx=15)
        
        self.botoes = {}
        for s, o in self.vm.produtos.items():
            def make_buy(slot=s):
                return lambda: self.comprar(slot)
            b = tk.Button(fp, text="", bg="#343a40", fg="white", anchor="w", command=make_buy())
            b.pack(fill="x", pady=2, padx=5)
            self.botoes[s] = b
            
        tk.Button(self.root, text="Devolver Saldo", bg="#dc3545", fg="white", command=self.devolver).pack(fill="x", pady=5, padx=15)
        self.atualizar_ecra()
        
    def comprar(self, s):
        n = self.ent_nif.get() if self.ent_nif.get().isdigit() and len(self.ent_nif.get()) == 9 else "999999999"
        if self.vm.comprar_produto(s, n):
            self.ent_nif.delete(0, tk.END)
            self.atualizar_ecra()

    def devolver(self):
        self.vm.devolver_saldo()
        self.atualizar_ecra()

    def validar(self):
        t = self.ent_nif.get()
        if self.vm.aplicar_voucher(t) or self.vm.autenticar_admin(t):
            self.ent_nif.delete(0, tk.END)
            self.atualizar_ecra()

    def simular_mbway(self):
        self.vm.saldo += Decimal("2.50")
        logger.info("MB WAY Ativo.")
        self.atualizar_ecra()

    def atualizar_ecra(self):
        self.lbl_saldo.config(text=f"{self.vm.saldo:.2f} EUR")
        for s, o in self.vm.produtos.items():
            self.botoes[s].config(text=f"{s} - {o['nome']} ({o['preco']:.2f} EUR) | Stock: {o['stock']}")

if __name__ == "__main__":
    vending = VendingMachine()
    app = VMUi(vending)
    app.root.mainloop()




import logging, os, threading
from decimal import Decimal

logger = logging.getLogger("VM"); logger.setLevel(logging.INFO)
sh = logging.StreamHandler(); sh.setFormatter(logging.Formatter("%(message)s")); logger.addHandler(sh)

class VendingMachine:
    def __init__(self):
        self.saldo = Decimal("0.00")
        self.produtos = {"1": {"nome": "Coca-Cola", "preco": Decimal("1.50")}, "2": {"nome": "Água", "preco": Decimal("1.00")}}
        self.on_vending_success = None

    def inserir_moeda(self, v: Decimal):
        self.saldo += v
        logger.info(f"🪙 Moeda de {v:.2f}€ adicionada.")

    def comprar_produto(self, s: str, nif: str = "999999999"):
        if s not in self.produtos: return False
        p = self.produtos[s]
        if self.saldo < p["preco"]: return False
        exc = self.saldo - p["preco"]; self.saldo = Decimal("0.00")
        if self.on_vending_success: self.on_vending_success(p["nome"])
        return True

class BKTerminalDisplay:
    def __init__(self, vm):
        self.vm = vm; self.id_c = 100; self.prep, self.prto = [], []
        self.vm.on_vending_success = self.novo_pedido

    def novo_pedido(self, nome):
        self.id_c += 1
        self.prep.append(f"#{self.id_c} {nome}")

    def atualizar_cozinha_manual(self):
        # Move o pedido de preparação para pronto, ou remove se já estiver pronto
        if self.prep:
            item = self.prep.pop(0)
            self.prto.append(item)
        elif self.prto:
            self.prto.pop(0)

    def desenhar_painel(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\033[H\033[J", end="")
        print("="*48 + "\n      NOXVIVA PRO - PAINEL DE SENHAS\n" + "="*48)
        print(f"{'PREPARAÇÃO (PREPARING)':<23} | {'PRONTO (READY)':<22}")
        print("-"*48)
        max_len = max(len(self.prep), len(self.prto), 1)
        for i in range(max_len):
            p = self.prep[i] if i < len(self.prep) else ""
            r = self.prto[i] if i < len(self.prto) else ""
            print(f"{p:<23} | {r:<22}")
        print("="*48)
        print(f"[ SALDO ATUAL: {self.vm.saldo:.2f}€ ]")

if __name__ == "__main__":
    vm = VendingMachine(); app = BKTerminalDisplay(vm)
    
    while True:
        app.desenhar_painel()
        print("\nPRODUTOS: [1] Coca-Cola (1.50€) | [2] Água (1.00€)")
        print("COMANDOS: M 2.00 (Moeda) | P 1 (Pedir) | C (Avançar Cozinha) | Q (Sair)")
        cmd = input("Comando > ").strip().upper()
        if cmd == 'Q': break
        
        try:
            if cmd.startswith("M "): vm.inserir_moeda(Decimal(cmd[2:]))
            elif cmd.startswith("P "): vm.comprar_produto(cmd[2:])
            elif cmd == "C": app.atualizar_cozinha_manual()
        except: pass
