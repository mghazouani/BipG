# Corriger les problèmes Flutter (Android + optionnel Windows)

À exécuter dans un terminal où **flutter** est reconnu (celui où tu as lancé `flutter doctor`).

---

## 1. Licences Android (obligatoire pour Android)

Dans PowerShell ou CMD :

```powershell
flutter doctor --android-licenses
```

À chaque question, tape **`y`** puis Entrée jusqu’à la fin. Ça règle « Android license status unknown ».

---

## 2. Android SDK Command-line Tools (cmdline-tools manquant)

**Option A – Via Android Studio (recommandé)**

1. Ouvre **Android Studio**.
2. **File** → **Settings** (ou **Android Studio** → **Preferences** sur Mac).
3. **Appearance & Behavior** → **System Settings** → **Android SDK**.
4. Onglet **SDK Tools**.
5. Coche **Android SDK Command-line Tools (latest)**.
6. Clique **Apply** / **OK** et attends la fin de l’installation.

**Option B – Sans Android Studio**

1. Télécharge les outils en ligne de commande :  
   https://developer.android.com/studio#command-line-tools-only  
   (prends **Command line tools only** pour Windows.)
2. Décompresse dans ton SDK Android, par exemple :  
   `C:\Users\TonUser\AppData\Local\Android\Sdk\cmdline-tools\latest\`
3. Vérifie que **ANDROID_HOME** pointe vers le dossier SDK (souvent `%LOCALAPPDATA%\Android\Sdk`).

---

## 3. Vérification

```powershell
flutter doctor
```

La section **Android toolchain** devrait être verte (ou avec une seule remarque mineure).

---

## 4. Visual Studio – pour les apps Windows desktop (`flutter run -d windows`)

Si `flutter doctor` affiche **Visual Studio is missing necessary components**, fais ceci :

### Étapes

1. **Ouvre Visual Studio Installer**  
   (menu Démarrer → « Visual Studio Installer », ou lance `C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe`).

2. **Modifier l’installation**  
   À côté de **Visual Studio Community 2022** (ou ton édition), clique sur **Modifier** (ou **More** → **Modify**).

3. **Choisir la charge de travail**  
   Dans l’onglet **Workloads** (Charge de travail) :
   - Coche **« Desktop development with C++ »** / **« Développement Desktop en C++ »**.

4. **Vérifier les composants (onglet Individual components)**  
   Clique sur l’onglet **Individual components** et assure-toi que ces éléments sont cochés :
   - **MSVC v142 - VS 2019 C++ x64/x86 build tools** (ou une version plus récente type **MSVC v143 - VS 2022 C++ x64/x86 build tools** si proposée – prends la plus récente).
   - **C++ CMake tools for Windows**.
   - **Windows 10 SDK** (ou **Windows 11 SDK** – une des deux suffit, souvent 10.0.19041 ou plus récent).

   Si tu restes dans l’onglet Workloads, la charge « Desktop development with C++ » installe normalement déjà ces composants ; en cas de doute, ouvre **Individual components** et vérifie les trois points ci-dessus.

5. **Lancer l’installation**  
   Clique **Modifier** (en bas à droite) et attends la fin du téléchargement et de l’installation (plusieurs Go possibles).

6. **Vérifier**  
   Ferme le terminal puis rouvre-le, puis exécute :
   ```powershell
   flutter doctor
   ```
   La section **Visual Studio** devrait être verte.

### Résumé des composants demandés par Flutter

| Composant | À cocher |
|-----------|----------|
| Charge de travail | **Desktop development with C++** |
| Outils de build | **MSVC v142** (VS 2019) ou **MSVC v143** (VS 2022) – x64/x86 |
| CMake | **C++ CMake tools for Windows** |
| SDK Windows | **Windows 10 SDK** (ou Windows 11 SDK) |

Tu peux lancer l’installer sans aller dans Individual components : cocher uniquement **Desktop development with C++** installe en général tout le nécessaire. Si `flutter doctor` signale encore un manque, rouvre le modificateur et ajoute le composant indiqué dans l’onglet **Individual components**.

---

## 5. Lancer les apps LIV

Une fois Android (et éventuellement Windows) OK :

**Client :**
```powershell
cd liv_client_app
flutter pub get
flutter run
```
Choisis **Chrome** ou un **émulateur / appareil Android**.

**Driver :**
```powershell
cd liv_driver_app
flutter pub get
flutter run
```

Pour l’émulateur Android, garde **`useAndroidEmulator = true`** dans `lib/config.dart` pour que l’API soit sur `10.0.2.2:8000`.
