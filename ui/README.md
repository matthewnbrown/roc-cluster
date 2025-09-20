# ROC Cluster Management UI

A modern React-based user interface for managing ROC accounts, built with TypeScript, Tailwind CSS, and React Query.

## Features

- **Account Management**: Create, read, update, and delete ROC accounts
- **Account Details**: View detailed account information including cookies and credit logs
- **Cookie Management**: Add, update, and delete account cookies
- **Credit Logs**: View credit transaction history for accounts
- **Search & Pagination**: Efficient browsing of large account lists
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Automatic data refreshing and optimistic updates

## Tech Stack

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **React Query** for data fetching and caching
- **React Hook Form** for form management
- **Axios** for API communication
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- ROC Cluster API running on `http://localhost:8000`

### Installation

1. Navigate to the UI directory:
   ```bash
   cd ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) to view the application

### Building for Production

```bash
npm run build
```

This creates a `build` folder with optimized production files.

## API Integration

The UI communicates with the ROC Cluster API through the following endpoints:

- `GET /api/v1/accounts` - List accounts with pagination
- `POST /api/v1/accounts` - Create new account
- `GET /api/v1/accounts/{id}` - Get account details
- `PUT /api/v1/accounts/{id}` - Update account
- `DELETE /api/v1/accounts/{id}` - Delete account
- `GET /api/v1/accounts/{id}/cookies` - Get account cookies
- `POST /api/v1/accounts/{id}/cookies` - Create/update cookies
- `DELETE /api/v1/accounts/{id}/cookies` - Delete cookies
- `GET /api/v1/accounts/{id}/credit-logs` - Get account credit logs

## Project Structure

```
ui/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── ui/           # Reusable UI components
│   │   ├── AccountList.tsx
│   │   ├── AccountForm.tsx
│   │   └── AccountDetails.tsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useAccounts.ts
│   │   ├── useCookies.ts
│   │   └── useCreditLogs.ts
│   ├── services/         # API service layer
│   │   └── api.ts
│   ├── types/            # TypeScript type definitions
│   │   └── api.ts
│   ├── App.tsx
│   ├── index.tsx
│   └── index.css
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## Key Components

### AccountList
- Displays paginated list of accounts
- Search functionality
- Action buttons for view, edit, and delete

### AccountForm
- Modal form for creating and editing accounts
- Form validation with React Hook Form
- Password field handling for updates

### AccountDetails
- Tabbed interface showing account overview, cookies, and credit logs
- Cookie management with JSON textarea
- Credit logs with pagination

## Environment Variables

Create a `.env` file in the `ui` directory to customize API settings:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## Development

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Code Style

The project uses:
- TypeScript for type safety
- ESLint for code linting
- Prettier for code formatting (recommended)
- Tailwind CSS for styling

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Use React Query for data fetching
4. Write responsive components with Tailwind CSS
5. Test your changes thoroughly

## License

This project is part of the ROC Cluster Management system.
