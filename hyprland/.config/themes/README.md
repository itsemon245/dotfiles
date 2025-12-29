# Waybar DRY Theme System (SCSS + GTK 3)

This configuration uses a **Sass (SCSS)** based architecture to generate GTK 3 compatible CSS. This overcomes GTK 3's limitations (no variables for non-color values) by using Sass variables and compilation.

## ⚠️ Workflow Changes

**DO NOT EDIT `style.css` DIRECTLY.**
Everything is generated from `style.scss` and the theme files.

### 📁 Directory Structure

```
waybar/
├── style.css           # ⛔ GENERATED FILE
├── style.scss          # ✅ Edit this for structural changes
└── themes/
    ├── _color-variants.scss  # Helper for opacity generation
    ├── temp-theme.scss       # Your theme file (colors + tokens)
    └── macchiato-dry.scss    # Example theme
```

## 🎨 Changing Themes

### 1. Create/Select a Theme File
Theme files (e.g., `themes/macchiato-dry.scss`) contain all tokens:
- **Colors**: `$primary`, `$bg`, `$success`...
- **Fonts**: `$font-family`, `$font-size`...
- **Dimensions**: `$radius`, `$padding`, `$margin`...

To create a new theme:
```bash
cp themes/macchiato-dry.scss themes/my-theme.scss
# Edit themes/my-theme.scss with your colors/fonts
```

### 2. Update the Import
Edit `themes/_current.scss` or symlink your theme to a standard name that `style.scss` imports.
**Current Setup**: `style.scss` imports `themes/current`.

```bash
# Link your desired theme to 'current'
ln -sf themes/my-theme.scss themes/_current.scss
```

### 3. Recompile CSS
You need `sass` installed.
```bash
sass style.scss style.css
```

### 4. Restart Waybar
```bash
killall waybar && waybar &
```

## 🛠️ Components

### Theme Files (`themes/*.scss`)
Define variables here. **No CSS rules**, just Sass variables.

```scss
/* Colors */
$bg: rgba(30, 30, 46, 1);
$primary: rgba(138, 173, 244, 1);

/* Typography */
$font-family: "JetBrainsMono Nerd Font";
$font-size: 14px;

/* Layout */
$radius: 12px;
$module-pad-x: 12px;
```

### Opacity Helper (`themes/_color-variants.scss`)
This helper automatically generates opacity variants (e.g., `$bg-90`, `$primary-20`) for standard palettes. You generally don't need to touch this.

### Main Stylesheet (`style.scss`)
This file:
1. Imports the theme (`@use "themes/current" as *;`)
2. Defines the actual CSS rules using the variables.

```scss
#waybar {
  background: $bg;
  font-family: $font-family;
}

#workspaces {
  border-radius: $radius;
  background: $surface;
}
```

## ❓ FAQ

**Why Sass?**
GTK 3 CSS does not support variables for `border-radius`, `padding`, `font-size`, etc. Sass allows us to use variables for *everything*, making the config truly DRY and themable.

**How do I adjust opacity?**
In your theme file, the `_color-variants.scss` module is used to generate variants.
To use them in `style.scss`:
```scss
background: $bg-90; // 90% opacity
color: $primary-50; // 50% opacity
```

**My changes aren't showing up!**
Did you run `sass style.scss style.css`? The `waybar` application only reads `style.css`.
