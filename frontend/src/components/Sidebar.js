import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSidebar } from '../context/SidebarContext';
import { useTheme } from '../context/ThemeContext';
import NotificationBell from './NotificationBell';
import {
  LayoutDashboard,
  Users,
  Briefcase, // 🆕 Icone para Equipe
  User,
  Wallet,
  Calculator,
  CreditCard,
  FileText,
  FileSignature,
  Bot,
  Bell,
  Settings,
  LogOut,
  ChevronRight,
  ChevronLeft,
  Menu,
  X,
  Download,
  ClipboardList,
  Crown,
  CreditCard as CardIcon,
  Sun,
  Moon,
  Shield,
  TrendingUp,
  ShoppingCart,
  Ticket,
  Clock,
  LifeBuoy,
  Smartphone,
  DatabaseBackup,
  CalendarClock,
  UserPlus,
  ScanSearch
} from 'lucide-react';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { isOpen, setIsOpen, isMobileOpen, setIsMobileOpen } = useSidebar();
  const { theme, toggleTheme, isDark } = useTheme();
  const [expandedMenus, setExpandedMenus] = React.useState({});

  // Auto-expandir submenu se estiver em uma rota do submenu
  React.useEffect(() => {
    if (location.pathname.startsWith('/emprestimos')) {
      setExpandedMenus(prev => ({ ...prev, '/emprestimos': true }));
    }
    if (location.pathname.startsWith('/whatsapp')) {
      setExpandedMenus(prev => ({ ...prev, '/whatsapp': true }));
    }
    if (location.pathname.startsWith('/auditoria') || location.pathname === '/whatsapp/logs') {
      setExpandedMenus(prev => ({ ...prev, '/auditoria': true }));
    }
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/';
    }
    return location.pathname === path;
  };

  const toggleSubmenu = (path) => {
    setExpandedMenus(prev => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  const isAdmin = user?.perfil === 'admin';

  // Menu principal - disponível para todos os usuários
  const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', testId: 'nav-dashboard', tourId: 'sidebar-dashboard' },
    { path: '/equipe', icon: Briefcase, label: 'Minha Equipe', testId: 'nav-equipe', tourId: 'sidebar-equipe' }, // 🆕 Minha Equipe
    { path: '/clientes', icon: User, label: 'Clientes', testId: 'nav-clientes', tourId: 'sidebar-clientes' },
    { path: '/aprovacoes', icon: UserPlus, label: 'Cadastros & Aprovações', testId: 'nav-aprovacoes', tourId: 'sidebar-aprovacoes' },
    { 
      path: '/emprestimos', 
      icon: Wallet, 
      label: 'Empréstimos', 
      testId: 'nav-emprestimos', 
      tourId: 'sidebar-emprestimos',
      submenu: [
        { path: '/emprestimos', label: 'Ativos', testId: 'nav-emprestimos-ativos' },
        { path: '/emprestimos/abertos', label: 'Abertos (Juros)', testId: 'nav-emprestimos-abertos' },
        { path: '/emprestimos/quitados', label: 'Quitados', testId: 'nav-emprestimos-quitados' }
      ]
    },
    { path: '/simulacao', icon: Calculator, label: 'Simulação', testId: 'nav-simulacao', tourId: 'sidebar-simulacao' },
    { path: '/pagamentos', icon: CreditCard, label: 'Pagamentos', testId: 'nav-pagamentos', tourId: 'sidebar-pagamentos' },
    { path: '/agenda', icon: CalendarClock, label: 'Agenda de Cobrança', testId: 'nav-agenda', tourId: 'sidebar-agenda' },
    { path: '/consultas', icon: ScanSearch, label: 'Consultas', testId: 'nav-consultas', tourId: 'sidebar-consultas' },
    { path: '/analise', icon: TrendingUp, label: 'Análise', testId: 'nav-analise', tourId: 'sidebar-analise' },
    { path: '/relatorios', icon: FileText, label: 'Relatórios', testId: 'nav-relatorios', tourId: 'sidebar-relatorios' },
    { path: '/contratos', icon: FileSignature, label: 'Contratos', testId: 'nav-contratos', tourId: 'sidebar-contratos' },
    { 
      path: '/whatsapp', 
      icon: Smartphone, 
      label: 'WhatsApp', 
      testId: 'nav-whatsapp', 
      tourId: 'sidebar-whatsapp',
      submenu: [
        { path: '/whatsapp', label: 'Conexões', testId: 'nav-whatsapp-conexoes' },
        { path: '/whatsapp/anti-spam', label: 'Anti-Spam', testId: 'nav-whatsapp-antispam' }
      ]
    },
    { path: '/config-notificacoes', icon: Settings, label: 'Config. Notificações', testId: 'nav-config-notificacoes', tourId: 'sidebar-config-notificacoes' }, // 🆕 Configurações de Notificações
    { path: '/assistente', icon: Bot, label: 'Assistente IA', testId: 'nav-assistente', tourId: 'sidebar-assistente' },
    { path: '/notificacoes', icon: Bell, label: 'Notificações', testId: 'nav-notificacoes', tourId: 'sidebar-notificacoes' },
    { path: '/suporte', icon: LifeBuoy, label: 'Suporte', testId: 'nav-suporte', tourId: 'sidebar-suporte' },
    { path: '/assinatura', icon: CardIcon, label: 'Assinatura', testId: 'nav-assinatura', tourId: 'sidebar-assinatura' },
    { path: '/exportacao', icon: Download, label: 'Exportar Dados', testId: 'nav-exportacao', tourId: 'sidebar-exportacao' },
  ].filter(item => {
    // Esconder "Minha Equipe" se for funcionário (owner_id != null)
    if (item.path === '/equipe') {
      return !user?.owner_id;
    }
    return true;
  });

  // Menu de usuário comum (não admin) - Perfil ao invés de Configurações
  const userMenuItems = [
    { path: '/perfil', icon: User, label: 'Meu Perfil', testId: 'nav-perfil', tourId: 'user-menu' },
  ];

  // Menu Super Admin - apenas para administradores
  const superAdminMenuItems = [
    { path: '/perfil', icon: User, label: 'Meu Perfil', testId: 'nav-admin-perfil' },
    { path: '/admin/usuarios', icon: Users, label: 'Usuários', testId: 'nav-admin-usuarios' },
    { path: '/admin/suporte', icon: LifeBuoy, label: 'Suporte', testId: 'nav-admin-suporte' },
    { path: '/admin/assinaturas', icon: CardIcon, label: 'Assinaturas', testId: 'nav-admin-assinaturas' },
    { path: '/admin/transacoes', icon: ShoppingCart, label: 'Transações', testId: 'nav-admin-transacoes' },
    { path: '/admin/cupons', icon: Ticket, label: 'Cupons', testId: 'nav-admin-cupons' },
    { path: '/admin/scheduler', icon: Clock, label: 'Jobs & Scheduler', testId: 'nav-admin-scheduler' },
    { path: '/admin/backup', icon: DatabaseBackup, label: 'Backup & Restore', testId: 'nav-admin-backup' },
    { 
      path: '/auditoria', 
      icon: ClipboardList, 
      label: 'Auditoria', 
      testId: 'nav-auditoria',
      submenu: [
        { path: '/auditoria', label: 'Logs Sistema', testId: 'nav-auditoria-sistema' },
        { path: '/whatsapp/logs', label: 'Logs WhatsApp', testId: 'nav-auditoria-whatsapp' }
      ]
    },
    { path: '/configuracoes', icon: Settings, label: 'Configurações', testId: 'nav-configuracoes', tourId: 'user-menu' },
    { path: '/superadmin', icon: Crown, label: 'Painel Admin', testId: 'nav-superadmin' },
  ];

  const NavItem = ({ item }) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    const hasSubmenu = item.submenu && item.submenu.length > 0;
    const isExpanded = expandedMenus[item.path];
    const isSubmenuActive = hasSubmenu && item.submenu.some(sub => isActive(sub.path));

    if (hasSubmenu) {
      return (
        <div>
          <button
            onClick={() => toggleSubmenu(item.path)}
            id={item.tourId}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
              isSubmenuActive
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent'
            } ${!isOpen ? 'lg:justify-center lg:px-2' : ''}`}
            data-testid={item.testId}
            title={!isOpen ? item.label : ''}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${
              isSubmenuActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
            }`} />
            <span className={`flex-1 truncate text-left ${!isOpen ? 'lg:hidden' : ''}`}>{item.label}</span>
            {isOpen && (
              <ChevronRight className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
            )}
          </button>
          
          {isExpanded && isOpen && (
            <div className="ml-8 mt-1 space-y-1">
              {item.submenu.map((subitem) => (
                <Link
                  key={subitem.path}
                  to={subitem.path}
                  onClick={() => setIsMobileOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                    isActive(subitem.path)
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent'
                  }`}
                  data-testid={subitem.testId}
                >
                  {subitem.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      );
    }

    return (
      <Link
        to={item.path}
        onClick={() => setIsMobileOpen(false)}
        id={item.tourId}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent'
          } ${!isOpen ? 'lg:justify-center lg:px-2' : ''}`}
        data-testid={item.testId}
        title={!isOpen ? item.label : ''}
      >
        <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
          }`} />
        <span className={`flex-1 truncate ${!isOpen ? 'lg:hidden' : ''}`}>{item.label}</span>
        {active && isOpen && <ChevronRight className="w-4 h-4 text-primary hidden sm:block" />}
      </Link>
    );
  };

  const AdminNavItem = ({ item }) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    const hasSubmenu = item.submenu && item.submenu.length > 0;
    const isExpanded = expandedMenus[item.path];
    const isSubmenuActive = hasSubmenu && item.submenu.some(sub => isActive(sub.path));

    if (hasSubmenu) {
      return (
        <div>
          <button
            onClick={() => toggleSubmenu(item.path)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
              isSubmenuActive
                ? 'bg-amber-500/20 text-amber-500'
                : 'text-muted-foreground hover:text-amber-400 hover:bg-amber-500/10'
            } ${!isOpen ? 'lg:justify-center lg:px-2' : ''}`}
            data-testid={item.testId}
            title={!isOpen ? item.label : ''}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${
              isSubmenuActive ? 'text-amber-500' : 'text-muted-foreground group-hover:text-amber-400'
            }`} />
            <span className={`flex-1 truncate text-left ${!isOpen ? 'lg:hidden' : ''}`}>{item.label}</span>
            {isOpen && (
              <ChevronRight className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
            )}
          </button>
          
          {isExpanded && isOpen && (
            <div className="ml-8 mt-1 space-y-1">
              {item.submenu.map((subitem) => (
                <Link
                  key={subitem.path}
                  to={subitem.path}
                  onClick={() => setIsMobileOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                    isActive(subitem.path)
                      ? 'bg-amber-500/20 text-amber-500 font-medium'
                      : 'text-muted-foreground hover:text-amber-400 hover:bg-amber-500/10'
                  }`}
                  data-testid={subitem.testId}
                >
                  {subitem.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      );
    }

    return (
      <Link
        to={item.path}
        onClick={() => setIsMobileOpen(false)}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${active
          ? 'bg-amber-500/20 text-amber-500'
          : 'text-muted-foreground hover:text-amber-400 hover:bg-amber-500/10'
          } ${!isOpen ? 'lg:justify-center lg:px-2' : ''}`}
        data-testid={item.testId}
        title={!isOpen ? item.label : ''}
      >
        <Icon className={`w-5 h-5 flex-shrink-0 transition-colors ${active ? 'text-amber-500' : 'text-muted-foreground group-hover:text-amber-400'
          }`} />
        <span className={`flex-1 truncate ${!isOpen ? 'lg:hidden' : ''}`}>{item.label}</span>
        {active && isOpen && <ChevronRight className="w-4 h-4 text-amber-500 hidden sm:block" />}
      </Link>
    );
  };

  return (
    <>
      {/* Mobile Header - Fixed top */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-card border-b border-border">
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="p-2.5 rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/30"
          data-testid="mobile-menu-button"
          aria-label="Menu"
        >
          {isMobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
        
        {/* Notification Bell no Mobile */}
        <NotificationBell />
      </div>

      {/* Desktop Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="hidden lg:flex fixed top-4 z-50 p-2 rounded-xl bg-sidebar border border-sidebar-border text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-all duration-300 shadow-lg"
        data-testid="desktop-toggle-button"
        style={{ left: isOpen ? '232px' : '56px' }}
      >
        {isOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-40 h-screen transition-all duration-300 ease-in-out bg-sidebar border-r border-sidebar-border flex flex-col
          ${isOpen ? 'lg:w-64' : 'lg:w-20'}
          ${isMobileOpen ? 'translate-x-0 w-72' : '-translate-x-full lg:translate-x-0'}
        `}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className={`flex items-center gap-3 px-4 sm:px-6 py-4 sm:py-5 border-b border-sidebar-border ${!isOpen ? 'lg:px-4 lg:justify-center' : ''}`}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center glow-primary flex-shrink-0">
            <span className="text-lg font-display font-bold text-white">GC</span>
          </div>
          <div className={`${!isOpen ? 'lg:hidden' : ''}`}>
            <h1 className="font-display font-bold text-lg text-foreground tracking-tight" data-testid="logo-link">
              <span className="text-primary">Gestor</span>Cred
            </h1>
            <p className="text-xs text-muted-foreground">Gestão de Empréstimos</p>
          </div>
        </div>

        {/* Theme Toggle & Notifications */}
        <div className={`px-3 py-3 border-b border-sidebar-border ${!isOpen ? 'lg:px-2' : ''}`}>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className={`flex-1 flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent ${!isOpen ? 'lg:justify-center lg:px-2' : ''
                }`}
              title={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
              data-testid="theme-toggle"
            >
              {isDark ? (
                <>
                  <Sun className="w-5 h-5 text-warning flex-shrink-0" />
                  <span className={`${!isOpen ? 'lg:hidden' : ''}`}>Tema Claro</span>
                </>
              ) : (
                <>
                  <Moon className="w-5 h-5 text-blue-400 flex-shrink-0" />
                  <span className={`${!isOpen ? 'lg:hidden' : ''}`}>Tema Escuro</span>
                </>
              )}
            </button>

            {/* Notification Bell - Desktop Only */}
            <div className="hidden lg:block">
              <NotificationBell />
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto scrollbar-thin">
          {/* Menu Principal */}
          <div className="space-y-1">
            {menuItems.map((item) => (
              <NavItem key={item.path} item={item} />
            ))}
          </div>

          {/* Menu de Usuário Comum - Quando NÃO é admin */}
          {!isAdmin && (
            <div className="mt-6">
              <div className={`flex items-center gap-2 mb-3 ${!isOpen ? 'lg:justify-center' : ''}`}>
                {isOpen && (
                  <>
                    <div className="flex-1 h-px bg-gradient-to-r from-primary/50 to-transparent"></div>
                    <div className="flex items-center gap-1.5 px-2">
                      <User className="w-3.5 h-3.5 text-primary" />
                      <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                        Minha Conta
                      </span>
                    </div>
                    <div className="flex-1 h-px bg-gradient-to-l from-primary/50 to-transparent"></div>
                  </>
                )}
                {!isOpen && (
                  <div className="hidden lg:block w-full h-px bg-primary/30"></div>
                )}
              </div>

              <div className="space-y-1">
                {userMenuItems.map((item) => (
                  <NavItem key={item.path} item={item} />
                ))}
              </div>
            </div>
          )}

          {/* Seção Super Admin - Apenas para Administradores */}
          {isAdmin && (
            <div className="mt-6">
              {/* Separador com título */}
              <div className={`flex items-center gap-2 mb-3 ${!isOpen ? 'lg:justify-center' : ''}`}>
                {isOpen && (
                  <>
                    <div className="flex-1 h-px bg-gradient-to-r from-amber-500/50 to-transparent"></div>
                    <div className="flex items-center gap-1.5 px-2">
                      <Shield className="w-3.5 h-3.5 text-amber-500" />
                      <span className="text-xs font-semibold text-amber-500 uppercase tracking-wider">
                        Super Admin
                      </span>
                    </div>
                    <div className="flex-1 h-px bg-gradient-to-l from-amber-500/50 to-transparent"></div>
                  </>
                )}
                {!isOpen && (
                  <div className="hidden lg:block w-full h-px bg-amber-500/30"></div>
                )}
              </div>

              {/* Items do Super Admin */}
              <div className="space-y-1">
                {superAdminMenuItems.map((item) => (
                  <AdminNavItem key={item.path} item={item} />
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* User Info & Logout */}
        <div className={`p-3 sm:p-4 border-t border-sidebar-border ${!isOpen ? 'lg:p-2' : ''}`}>
          <div className={`bg-sidebar-accent rounded-xl p-3 mb-3 ${!isOpen ? 'lg:hidden' : ''}`}>
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${isAdmin
                ? 'bg-gradient-to-br from-amber-500/20 to-amber-600/40'
                : 'bg-gradient-to-br from-primary/20 to-primary/40'
                }`}>
                <span className={`text-sm font-semibold ${isAdmin ? 'text-amber-500' : 'text-primary'}`}>
                  {user?.nome?.charAt(0)?.toUpperCase() || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate" data-testid="user-name">
                  {user?.nome}
                </p>
                <p className="text-xs text-muted-foreground truncate" data-testid="user-email">
                  {user?.email}
                </p>
              </div>
            </div>
            <div className="mt-2">
              <span
                className={`text-xs px-2 py-1 rounded-full ${isAdmin
                  ? 'bg-amber-500/10 text-amber-500'
                  : 'bg-primary/10 text-primary'
                  }`}
                data-testid="user-role"
              >
                {isAdmin ? '👑 Administrador' : 'Operador'}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors ${!isOpen ? 'lg:justify-center' : 'justify-center'
              }`}
            data-testid="logout-button"
            title={!isOpen ? 'Sair' : ''}
          >
            <LogOut className="w-5 h-5" />
            <span className={`${!isOpen ? 'lg:hidden' : ''}`}>Sair</span>
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
