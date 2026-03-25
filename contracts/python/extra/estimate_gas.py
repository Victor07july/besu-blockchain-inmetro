"""
Estimativa de gas para contratos ERC-721 com OpenZeppelin
"""

print("📊 ESTIMATIVA DE GAS PARA DEPLOY")
print("=" * 60)
print()

# Referências de contratos similares:
print("🔹 ERC-721 básico (sem extensions): ~2.5M gas")
print("🔹 ERC-721 + Enumerable: ~3.5M gas")
print("🔹 ERC-721 + Enumerable + Ownable: ~3.8M gas")
print("🔹 ERC-721 + Enumerable + Ownable + ReentrancyGuard: ~4M gas")
print()

print("�� Seu contrato CarbonCreditNFT_E2 inclui:")
print("   ✅ ERC-721")
print("   ✅ ERC-721Enumerable")
print("   ✅ ReentrancyGuard")
print("   ✅ Ownable")
print("   ✅ Struct complexa com 12 parâmetros")
print("   ✅ Cálculos matemáticos extensos")
print("   ✅ Múltiplos mappings")
print("   ✅ Eventos customizados")
print()

print("💡 RECOMENDAÇÕES:")
print("=" * 60)
print()
print("🎯 Gas Limit Recomendado: 6.000.000 (6M)")
print("   - Margem de segurança para deploy completo")
print("   - Cobre toda a lógica + OpenZeppelin")
print()
print("⚠️  Gas Limit Mínimo: 4.500.000 (4.5M)")
print("   - Pode funcionar, mas arriscado")
print()
print("❌ Seu deploy anterior: 5.000.000")
print("   - Gas usado reportado: 53.000 (INCORRETO!)")
print("   - Provável: Out of Gas silencioso")
print()
print("🚀 Para deploy via Postman, use:")
print('   "gas_limit": 6000000')
print()

