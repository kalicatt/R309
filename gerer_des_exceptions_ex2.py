def divEntier(x: int, y: int) -> int:
    # Vérifier si l'un des nombres est négatif ou si y est égal à 0
    if x < 0 or y < 0:
        raise ValueError("Les deux nombres doivent être positifs.")
    if y == 0:
        raise ValueError("Le diviseur y ne peut pas être égal à 0.")
    
    # Division entière récursive
    if x < y:
        return 0
    else:
        x = x - y
        return divEntier(x, y) + 1

def main():
    try:
        # Saisie des valeurs de x et y
        x = int(input("Entrez la valeur de x (entier positif): "))
        y = int(input("Entrez la valeur de y (entier positif): "))
        
        # Appel de la fonction divEntier et affichage du résultat
        resultat = divEntier(x, y)
        print(f"Le résultat de la division entière de {x} par {y} est: {resultat}")
    except ValueError as e:
        # Affichage du message d'erreur correspondant
        print(f"Erreur: {e}")

# Exécution de la fonction main
main()



"""
La tentative d'exécuter la fonction main qui utilise input a échoué car l'environnement dans lequel le code est exécuté ne prend pas en charge les entrées standard. En d'autres termes, nous ne pouvons pas utiliser input pour saisir des données de l'utilisateur ici.

Cependant, le code que j'ai fourni est correct et peut être exécuté dans un environnement Python local sur votre ordinateur. Si vous exécutez ce code localement, il vous demandera de saisir les valeurs pour x et y, et si vous saisissez une valeur non entière ou 0 pour y, il gérera l'exception ValueError en affichant le message d'erreur approprié.

"""