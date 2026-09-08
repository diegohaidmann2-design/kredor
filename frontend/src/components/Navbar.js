import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path ? 'bg-blue-700' : '';
  };

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/" className="text-xl font-bold" data-testid="logo-link">
              GestorCred - Sistema de Gestão de Empréstimos
            </Link>
            <div className="hidden md:flex space-x-4">
              <Link
                to="/"
                className={`px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition ${isActive('/')}`}
                data-testid="nav-dashboard"
              >
                Dashboard
              </Link>
              <Link
                to="/clientes"
                className={`px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition ${isActive('/clientes')}`}
                data-testid="nav-clientes"
              >
                Clientes
              </Link>
              <Link
                to="/emprestimos"
                className={`px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition ${isActive('/emprestimos')}`}
                data-testid="nav-emprestimos"
              >
                Empréstimos
              </Link>
              <Link
                to="/simulacao"
                className={`px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition ${isActive('/simulacao')}`}
                data-testid="nav-simulacao"
              >
                Simulação
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm" data-testid="user-name">{user?.nome}</span>
            <span className="text-xs px-2 py-1 bg-blue-700 rounded" data-testid="user-role">
              {user?.perfil === 'admin' ? 'Admin' : 'Operador'}
            </span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded-md text-sm font-medium transition"
              data-testid="logout-button"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
