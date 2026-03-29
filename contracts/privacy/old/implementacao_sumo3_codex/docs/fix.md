# Correcoes Aplicadas no Script de Analise de Distancia

Script de referencia:
- ../scripts/process_sumo_osmnx_harversine_fix.py

## Explicacao Tecnica

Foram aplicadas duas correcoes estruturais para eliminar inflacao artificial da distancia do trajeto original.

1. Ordenacao estavel dos pontos do trajeto
- Problema anterior: o agrupamento era ordenado apenas por start_time.
- Efeito colateral: quando varias linhas tinham o mesmo timestamp, a sequencia podia ficar inconsistente (zig-zag), aumentando a soma Haversine entre pontos consecutivos.
- Correcao aplicada:
	- criacao de coluna auxiliar _row_order com a ordem original do CSV;
	- ordenacao estavel por start_time, end_time e _row_order usando mergesort.
- Resultado tecnico: a sequencia espacial/temporal dos pontos fica deterministica, reduzindo saltos artificiais.

2. Distancia SUMO acumulada calculada por maximo
- Problema anterior: uso de iloc[-1] em colunas acumuladas (distance, distance_city, distance_highway).
- Risco: se a ordem do grupo variar, o ultimo registro pode nao representar o valor acumulado final correto.
- Correcao aplicada:
	- conversao numerica com pd.to_numeric(..., errors='coerce');
	- uso de max() para extrair a distancia acumulada robusta;
	- fallback para 0.0 quando o valor for NaN.
- Resultado tecnico: Distancia_SUMO_km passa a representar o acumulado correto mesmo com variacao de ordenacao.

## Explicacao Simples (Facil de Entender)

Antes, o script podia montar o caminho do carro fora de ordem quando varios pontos tinham o mesmo horario. Isso fazia a distancia calculada parecer muito maior do que a distancia real do SUMO.

Agora ele:
- respeita a ordem original das linhas para nao embaralhar os pontos;
- pega a distancia acumulada do SUMO pelo maior valor (mais seguro) em vez de pegar apenas a ultima linha.

Na pratica, isso fez as duas distancias ficarem coerentes. Exemplo observado no teste:
- Distancia_SUMO_km: 0,3921
- Distancia_Trajeto_Original_km: 0,3914

Ou seja, ficaram praticamente iguais, como esperado.

