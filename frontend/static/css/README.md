## 🎨 Customizing the Theme for Your University or Organization

This project uses centralized CSS variables to make it easy for institutions to apply their own branding.

### 🔧 Steps to Customize

1. **Update the brand colors in `style.css`**

   Open `style.css` and scroll to the `:root` section at the top:

   ```css
   :root {
       --primary-color: #012169;         /* Replace with your main brand color */
       --primary-hover: #0b2a6b;         /* Hover state for primary buttons */
       --accent-color: #00539B;          /* Secondary accent color */
       --accent-hover: #004080;          /* Hover state for success buttons */
       --warning-color: #ffc107;
       --warning-hover: #e0a800;
       --warning-border-hover: #d39e00;
       --text-light: #ffffff;
       --text-muted: #e0e0e0;
       --bg-light: #f4f4f4;
   }

Update university logos and headers:
   - Modify the `<img>` in `sidebar.html` (and any other HTML templates)
   - Replace the logo source path and `alt` text with your own branding.