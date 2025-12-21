# Creating Opacity Variants - GTK 3 Guide

With RGBA values in `@define-color`, you can easily create opacity variants of your colors.

## GTK 3 Syntax

GTK 3 uses `@define-color` for colors and `@color-name` to reference them:

```css
/* Define color */
@define-color primary rgba(138, 173, 244, 1);

/* Use color */
#waybar {
  background: @primary;
}
```

## Creating Opacity Variants

### Method: Define Multiple Variants in Theme File

```css
/* Base color */
@define-color primary rgba(138, 173, 244, 1);

/* Create opacity variants */
@define-color primary-90 rgba(138, 173, 244, 0.9);
@define-color primary-80 rgba(138, 173, 244, 0.8);
@define-color primary-50 rgba(138, 173, 244, 0.5);
@define-color primary-20 rgba(138, 173, 244, 0.2);
@define-color primary-10 rgba(138, 173, 244, 0.1);
```

Then use in `style.css`:

```css
#waybar {
  background: @primary-90;  /* 90% opacity */
}

#workspaces button:hover {
  background: @primary-20;  /* 20% opacity for subtle highlight */
}
```

## Common Use Cases

### Semi-transparent Background

```css
/* In theme file */
@define-color bg rgba(36, 39, 58, 1);
@define-color bg-90 rgba(36, 39, 58, 0.9);
@define-color bg-80 rgba(36, 39, 58, 0.8);

/* In style.css */
#waybar {
  background: @bg-90;  /* Semi-transparent waybar */
}
```

### Hover Effects

```css
/* In theme file */
@define-color primary rgba(138, 173, 244, 1);
@define-color primary-20 rgba(138, 173, 244, 0.2);

/* In style.css */
#workspaces button {
  background: @transparent;
}

#workspaces button:hover {
  background: @primary-20;  /* Subtle highlight on hover */
}
```

### Module Backgrounds

```css
/* In theme file */
@define-color surface rgba(54, 58, 79, 1);
@define-color surface-90 rgba(54, 58, 79, 0.9);
@define-color surface-50 rgba(54, 58, 79, 0.5);

/* In style.css */
#clock, #battery {
  background: @surface-90;  /* Slightly transparent modules */
}
```

### Overlays and Borders

```css
/* In theme file */
@define-color black rgba(24, 25, 38, 1);
@define-color black-80 rgba(24, 25, 38, 0.8);
@define-color black-50 rgba(24, 25, 38, 0.5);

@define-color border rgba(91, 96, 120, 1);
@define-color border-50 rgba(91, 96, 120, 0.5);

/* In style.css */
.overlay {
  background: @black-80;  /* 80% opaque overlay */
}

#clock {
  border-right: 1px solid @border-50;  /* Semi-transparent border */
}
```

## Converting Hex to RGBA

If you have a hex color and want to convert it to RGBA:

### Manual Conversion

1. **Hex to RGB**: `#8aadf4`
   - R: `8a` = 138
   - G: `ad` = 173
   - B: `f4` = 244

2. **RGB to RGBA**: `rgba(138, 173, 244, 1)`

3. **Add opacity**: `rgba(138, 173, 244, 0.5)` for 50%

### Online Tools

- [RGB Color Converter](https://www.rgbtohex.net/)
- [Color Picker](https://htmlcolorcodes.com/color-picker/)
- Browser DevTools color picker

## Example: Glass Effect

```css
/* In theme file */
@define-color bg rgba(36, 39, 58, 1);
@define-color bg-70 rgba(36, 39, 58, 0.7);

@define-color fg rgba(202, 211, 245, 1);
@define-color fg-10 rgba(202, 211, 245, 0.1);

/* In style.css */
#waybar {
  background: @bg-70;  /* Semi-transparent background */
  border: 1px solid @fg-10;  /* Subtle border */
}
```

**Note**: GTK 3 CSS doesn't support `backdrop-filter`, so true glass/blur effects aren't possible.

## Opacity Levels Reference

Common opacity levels and their use cases:

- **1.0 (100%)** - Fully opaque, standard colors
- **0.9 (90%)** - Slightly transparent, good for backgrounds
- **0.8 (80%)** - Noticeably transparent, still readable
- **0.7 (70%)** - More transparent, glass-like effect
- **0.5 (50%)** - Half transparent, overlays
- **0.3 (30%)** - Very transparent, subtle effects
- **0.2 (20%)** - Barely visible, hover highlights
- **0.1 (10%)** - Almost invisible, subtle borders
- **0.0 (0%)** - Fully transparent

## Best Practices

1. **Define variants in theme file** - Keep all color definitions in one place
2. **Use semantic names** - `primary-80` is clearer than `primary-transparent`
3. **Test readability** - Ensure text is readable on transparent backgrounds
4. **Consistent opacity levels** - Use standard levels (90, 80, 50, 20, 10)
5. **RGBA over hex** - Easier to create opacity variants

## Example Theme with Opacity Variants

```css
/* macchiato-dry.css */

/* Base colors */
@define-color primary rgba(138, 173, 244, 1);
@define-color bg rgba(36, 39, 58, 1);
@define-color surface rgba(54, 58, 79, 1);

/* Opacity variants */
@define-color primary-80 rgba(138, 173, 244, 0.8);
@define-color primary-50 rgba(138, 173, 244, 0.5);
@define-color primary-20 rgba(138, 173, 244, 0.2);

@define-color bg-90 rgba(36, 39, 58, 0.9);
@define-color bg-80 rgba(36, 39, 58, 0.8);
@define-color bg-50 rgba(36, 39, 58, 0.5);

@define-color surface-90 rgba(54, 58, 79, 0.9);
@define-color surface-80 rgba(54, 58, 79, 0.8);
@define-color surface-50 rgba(54, 58, 79, 0.5);
```

Then use in `style.css`:

```css
#waybar {
  background: @bg-90;  /* Semi-transparent waybar */
}

#workspaces {
  background: @surface-90;
}

#workspaces button:hover {
  background: @primary-20;  /* Subtle hover effect */
}

#clock, #battery {
  background: @surface-80;
}
```

## GTK 3 Limitations

Remember:
- ✅ Can use `@define-color` for colors with RGBA
- ✅ Can reference colors with `@color-name`
- ❌ Cannot use `--variable` or `var()` syntax
- ❌ Cannot variablize non-color values (spacing, fonts, etc.)
