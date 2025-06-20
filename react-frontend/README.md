# Black Hole Router - React Frontend

This is the React TypeScript frontend for the Black Hole Router application, migrated from Flask templates while maintaining the exact same UI and functionality.

## 🚀 Features

- **Dashboard**: Interactive charts showing blocklist statistics, timeline data, and recent activity with date filtering
- **Blocklist Management**: Full CRUD operations, bulk delete, CSV upload, search, and sorting
- **Safelist Management**: Manage safelisted IPs with permanent/temporary options
- **User Management**: User administration with role-based access
- **Responsive Design**: Bootstrap-based UI that works on desktop and mobile
- **TypeScript**: Full type safety for better development experience

## 📁 Project Structure

```
react-frontend/
├── public/
│   ├── images/
│   │   └── dukeLogo.png
│   └── index.html
├── src/
│   ├── components/
│   │   └── Layout/
│   │       ├── Layout.tsx
│   │       ├── Layout.css
│   │       ├── Sidebar.tsx
│   │       └── Sidebar.css
│   ├── pages/
│   │   ├── Dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Dashboard.css
│   │   ├── Blocklist/
│   │   │   ├── Blocklist.tsx
│   │   │   └── Blocklist.css
│   │   ├── Safelist/
│   │   │   ├── Safelist.tsx
│   │   │   └── Safelist.css
│   │   └── Users/
│   │       ├── Users.tsx
│   │       └── Users.css
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── App.css
│   └── index.tsx
└── package.json
```

## 🛠️ Technologies Used

- **React 18** with TypeScript
- **React Router DOM** for client-side routing
- **Bootstrap 5** & **React Bootstrap** for UI components
- **Chart.js** & **React Chart.js 2** for interactive charts
- **Axios** for HTTP requests
- **CSS Custom Properties** for Duke University branding

## 🎨 Design System

The app maintains Duke University's branding with:
- **Primary Color**: `#012169` (Duke Blue)
- **Accent Color**: `#00539B` 
- **Warning Color**: `#ffc107`
- **Typography**: Segoe UI font family
- **Responsive**: Mobile-first Bootstrap grid system

## 📡 API Integration

The frontend communicates with the Flask backend through a centralized API service:

- **Dashboard API**: `/dashboard/data`, `/dashboard/api/filter_stats`
- **Blocklist API**: `/blocklist/*` - CRUD, search, CSV upload, bulk operations
- **Safelist API**: `/safelist/*` - CRUD, search operations
- **Users API**: `/users/*` - User management operations

## 🚀 Development

### Prerequisites

- Node.js 16+ and npm
- Flask backend running on `http://localhost:5000`

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The app will open at `http://localhost:3000` and automatically proxy API requests to the Flask backend.

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## 🏗️ Production Build

To build the optimized production version:

```bash
npm run build
```

This creates a `build/` directory with optimized static files that can be served by the Flask backend.

## 🔧 Backend Integration

The Flask backend (`app.py`) has been updated to:

1. **Serve React Build**: Automatically serve React build files when available
2. **Handle Routing**: Support client-side React Router routes
3. **CORS Support**: Enable cross-origin requests for development
4. **Fallback**: Fall back to Flask templates if React build doesn't exist

### Environment Variables

Create a `.env` file in the React frontend directory for custom configuration:

```env
REACT_APP_API_URL=http://localhost:5000
```

## 🚀 Deployment Options

### Option 1: Integrated with Flask
1. Build the React app: `npm run build`
2. Flask will automatically serve the React build
3. All routes handled by single Flask server

### Option 2: Separate Deployment
1. Deploy React build to static hosting (Vercel, Netlify)
2. Update `REACT_APP_API_URL` to point to Flask backend
3. Deploy Flask backend separately

## 🔍 Key Features Migrated

### Dashboard
- ✅ Interactive Chart.js charts (Bar, Line, Pie)
- ✅ Statistical cards with click-to-filter functionality  
- ✅ Date range filtering with quick filter options
- ✅ Recent activity table
- ✅ Real-time data updates

### Blocklist
- ✅ Sortable table with all columns
- ✅ Search functionality
- ✅ Add/Edit/Delete operations
- ✅ Bulk delete with checkbox selection
- ✅ CSV file upload
- ✅ Form validation

### Safelist  
- ✅ Full CRUD operations
- ✅ Permanent vs temporary entries
- ✅ Search and sorting
- ✅ Date/time handling

### Users
- ✅ User management with roles
- ✅ Statistics dashboard
- ✅ Search functionality
- ✅ Add/Edit/Delete operations

## 🎯 Migration Benefits

1. **Modern Development**: React + TypeScript for better maintainability
2. **Performance**: Client-side routing, optimized builds
3. **User Experience**: Improved interactivity and responsiveness  
4. **Developer Experience**: Hot reloading, component architecture
5. **Scalability**: Easier to extend and maintain
6. **Type Safety**: Comprehensive TypeScript interfaces

## 🐛 Known Issues & Limitations

- ESLint warnings about useEffect dependencies (non-blocking)
- API calls currently don't include authentication headers
- Some form validations could be enhanced client-side

## 📝 Future Enhancements

- Add authentication/authorization
- Implement client-side caching
- Add real-time updates with WebSockets
- Enhanced error handling and loading states
- Unit and integration tests
- PWA capabilities

---

**Migration completed successfully** ✅
All original functionality preserved with modern React architecture.
