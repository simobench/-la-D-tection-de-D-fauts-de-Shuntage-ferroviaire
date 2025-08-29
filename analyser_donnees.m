function n = analyser_donnees(indices, valeurs)
    % indices et valeurs sont passés depuis Python
    Reet = valeurs;              % Ta liste de Z injectée
    Vecteur_TempsRe = indices;   % Ton vecteur d'indices injecté

    % Affichage pour debug
    disp('○ Données reçues dans MATLAB (via arguments) :')
    disp('Indices :')
    disp(Vecteur_TempsRe)
    disp('Valeurs :')
    disp(Reet)

    % Exemple de traitement : retourner le nombre d’éléments
    n = length(valeurs);
end
