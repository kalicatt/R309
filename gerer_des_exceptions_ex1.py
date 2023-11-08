# Définition de la fonction divEntier comme fournie dans l'exemple.
def divEntier(x: int, y: int) -> int:
    if x < y:
        return 0
    else:
        x = x - y
        return divEntier(x, y) + 1

# Exécution de la fonction avec les valeurs 10 et 2.
divEntier(10, 2)


"""
    La fonction divEntier prend deux arguments x et y, qui sont des entiers.
    Si x est inférieur à y, la fonction retourne 0 car dans la division entière, si le dividende est inférieur au diviseur, le quotient est 0.
    Si x est égal ou supérieur à y, la fonction soustrait y de x et appelle récursivement divEntier avec la nouvelle valeur de x et la même valeur de y.
    Chaque appel récursif ajoute 1 au résultat final, ce qui est équivalent à compter combien de fois y peut être soustrait de x avant que x ne devienne inférieur à y.

Pour répondre à la deuxième question, nous pouvons essayer la fonction avec deux valeurs simples, par exemple divEntier(10, 2). Cela devrait retourner 5 car 2 peut être soustrait de 10 cinq fois avant que le résultat ne soit inférieur à 2.
Le résultat de l'exécution de divEntier(10, 2) est 5, ce qui signifie que la fonction a correctement calculé la division entière de 10 par 2, indiquant que 2 peut être soustrait de 10 cinq fois avant que le résultat ne soit inférieur à 2
"""