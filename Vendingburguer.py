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
