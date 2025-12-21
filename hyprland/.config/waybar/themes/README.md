# Waybar DRY Theme System (GTK 3 Compatible)

This directory contains theme files for Waybar using a DRY approach **within GTK 3's limitations**.

## ⚠️ Important: GTK 3 CSS Limitations

Waybar uses **GTK 3 CSS**, which has significant limitations compared to standard web CSS:

### ✅ What You CAN Variablize
- **Colors only** using `@define-color` and `@color-name` syntax
- RGBA values for opacity control

### ❌ What You CANNOT Variablize
- Font sizes, font weights, font families
- Margins, padding, spacing
- Border radius, border width
- Any numeric values or dimensions

**Solution**: Use **grouped selectors** in `style.css` to share common properties.

## Quick Start

The active theme is determined by the `default.css` symlink:

```bash
ln -sf <theme-name>.css default.css
killall waybar && waybar &
```

## Available Themes

- **macchiato-dry.css** - Catppuccin Macchiato with comprehensive color palette
- **macchiato.css** - Original Catppuccin Macchiato (colors only)

## Creating a New Theme

### 1. Copy the Template

```bash
cp macchiato-dry.css my-theme.css
```

### 2. Customize Colors

You can **only** customize colors using `@define-color`:

```css
/* Basic Colors */
@define-color primary    rgba(255, 107, 107, 1);
@define-color bg         rgba(26, 26, 46, 1);
@define-color fg         rgba(238, 238, 238, 1);

/* Semantic Colors */
@define-color destructive rgba(255, 107, 107, 1);
@define-color warning     rgba(255, 212, 59, 1);
@define-color success     rgba(81, 207, 102, 1);

/* RGB Colors */
@define-color red         rgba(255, 107, 107, 1);
@define-color green       rgba(81, 207, 102, 1);
@define-color blue        rgba(100, 149, 237, 1);

/* CMYK Colors */
@define-color cyan        rgba(0, 255, 255, 1);
@define-color magenta     rgba(255, 0, 255, 1);
@define-color yellow      rgba(255, 255, 0, 1);
@define-color black       rgba(0, 0, 0, 1);

/* Surfaces */
@define-color surface     rgba(40, 40, 60, 1);
@define-color border      rgba(80, 80, 100, 1);

/* Opacity Variants */
@define-color primary-80  rgba(255, 107, 107, 0.8);
@define-color bg-90       rgba(26, 26, 46, 0.9);
```

### 3. Customize Spacing/Fonts (in style.css)

To change fonts, spacing, or other non-color values, edit `style.css`:

```css
/* Change global font */
* {
  font-family: "JetBrainsMono Nerd Font";
  font-size: 14px;  /* Change base size */
}

/* Change module spacing */
#custom-music,
#tray,
#clock,
#battery {
  padding: 0.3rem 0.8rem;  /* Adjust padding */
  margin: 3px 0;            /* Adjust margin */
}

/* Change border radius */
#workspaces {
  border-radius: 0.5rem;  /* Smaller radius */
}
```

### 4. Activate Your Theme

```bash
ln -sf my-theme.css default.css
killall waybar && waybar &
```

## Color Naming Convention

The theme uses consistent, semantic color names:

### Basic Colors
- `primary` - Main accent color
- `bg` - Background
- `fg` - Foreground/text

### Semantic Colors
- `destructive`/`danger` - Error states
- `warning` - Warning states
- `success` - Success states
- `info` - Informational
- `transparent` - Fully transparent

### RGB Colors
- `red`, `green`, `blue`

### CMYK Colors
- `cyan`, `magenta`, `yellow`, `black`

### Surfaces
- `surface` - Module backgrounds
- `surface-variant` - Alternative surface
- `border` - Border colors

## RGBA Opacity Control

Use RGBA values to create opacity variants:

```css
/* Full opacity */
@define-color primary rgba(138, 173, 244, 1);

/* Opacity variants */
@define-color primary-80 rgba(138, 173, 244, 0.8);  /* 80% */
@define-color primary-50 rgba(138, 173, 244, 0.5);  /* 50% */
@define-color primary-20 rgba(138, 173, 244, 0.2);  /* 20% */
```

Then use in `style.css`:

```css
#waybar {
  background: @bg-90;  /* 90% opaque background */
}

#workspaces button:hover {
  background: @primary-20;  /* Subtle highlight */
}
```

## DRY Approach for Non-Color Values

Since GTK 3 doesn't support variables for spacing/fonts, use **grouped selectors**:

```css
/* Group modules with same padding */
#clock, #battery, #network, #bluetooth {
  padding: 0.5rem 1rem;
  margin: 5px 0;
}

/* Group modules with same border radius */
#custom-music, #custom-netspeed, #custom-memory {
  border-radius: 1rem;
}

/* Group modules with same font size */
#custom-netspeed, #custom-memory {
  font-size: 14px;
  font-weight: bold;
}
```

## Important Notes

- **GTK 3 limitation**: Only colors can use variables
- **Use RGBA**: Easier opacity control than hex
- **Grouped selectors**: Best way to stay DRY for non-color values
- **Official docs**: Always refer to [Waybar Wiki on GitHub](https://github.com/Alexays/Waybar/wiki)
- **Not waybar.org**: That site has incorrect information about CSS variables

## Theme Examples

### Minimal Dark Theme

```css
@define-color primary    rgba(255, 255, 255, 1);
@define-color bg         rgba(0, 0, 0, 1);
@define-color fg         rgba(255, 255, 255, 1);
@define-color surface    rgba(26, 26, 26, 1);
@define-color transparent rgba(0, 0, 0, 0);
/* ... define all other required colors ... */
```

### Colorful Theme

```css
@define-color primary    rgba(255, 107, 107, 1);
@define-color bg         rgba(26, 26, 46, 1);
@define-color fg         rgba(238, 238, 238, 1);
@define-color success    rgba(81, 207, 102, 1);
@define-color warning    rgba(255, 212, 59, 1);
@define-color destructive rgba(255, 107, 107, 1);
/* ... define all other required colors ... */
```

## Troubleshooting

**Waybar won't start:**
```bash
waybar --log-level debug
```

**CSS errors:**
- Check that you're only using `@define-color` for colors
- Ensure all color values are valid (hex or rgba)
- Don't try to use `--variable` or `var()` syntax

**Symlink not working:**
```bash
ls -la default.css  # Check symlink target
```

## Converting Hex to RGBA

```bash
# Hex: #8aadf4
# RGB: (138, 173, 244)
# RGBA: rgba(138, 173, 244, 1)
# 50% opacity: rgba(138, 173, 244, 0.5)
```

Use online converters or color pickers to convert hex to RGBA.
