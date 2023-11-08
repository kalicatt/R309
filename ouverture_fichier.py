# Nom du fichier à ouvrir
nom_du_fichier = "fichier.txt"

try:
    # Ouverture du fichier en mode lecture
    with open(nom_du_fichier, 'r') as fichier:
        # Affichage des lignes du fichier
        for ligne in fichier:
            ligne = ligne.rstrip("\n\r")
            print(ligne)
except FileNotFoundError:
    print("Le fichier spécifié n'a pas été trouvé.")
except IOError:
    print("Une erreur d'entrée/sortie s'est produite.")
except FileExistsError:
    print("Le fichier existe déjà.")
except PermissionError:
    print("Permission refusée pour accéder au fichier.")
finally:
    print("Fin du programme.")


"""
Nous utilisons un bloc try pour essayer d'exécuter des instructions qui peuvent potentiellement lever une exception.
with open() est utilisé pour ouvrir le fichier. Cette méthode est préférée car elle s'assure que le fichier est bien fermé après la lecture, même si une exception est levée.
Nous parcourons chaque ligne du fichier, en retirant les caractères de fin de ligne avec rstrip().
Dans le bloc except, nous attrapons et traitons les exceptions spécifiques qui pourraient être levées lors de l'ouverture ou de la lecture du fichier.
Le bloc finally s'exécute toujours, peu importe si une exception a été levée ou non, indiquant la fin du programme.

"""