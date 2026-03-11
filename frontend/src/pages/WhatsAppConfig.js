import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { whatsappAPI } from '../api/api';
import { Smartphone, RefreshCw, Trash2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const WhatsAppConfig = () => {
    const [conexoes, setConexoes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [criandoConexao, setCriandoConexao] = useState(false);
    const [evolutionConfigured, setEvolutionConfigured] = useState(null);
    const { toast } = useToast();

    useEffect(() => {
        carregarConexoes();
        verificarEvolutionAPI();
    }, []);

    const verificarEvolutionAPI = async () => {
        try {
            const response = await whatsappAPI.obterConfigEvolution();
            setEvolutionConfigured(response.data.habilitado && response.data.api_url && response.data.api_key);
        } catch (error) {
            setEvolutionConfigured(false);
        }
    };

    const carregarConexoes = async () => {
        try {
            const response = await whatsappAPI.listarConexoes();
            setConexoes(response.data.items);
        } catch (error) {
            console.error('Erro ao carregar conexões:', error);
        } finally {
            setLoading(false);
        }
    };

    const criarNovaConexao = async () => {
        try {
            setCriandoConexao(true);
            const response = await whatsappAPI.criarConexao();
            await carregarConexoes();
            
            // Iniciar polling de status
            iniciarVerificacaoStatus(response.data.id);
        } catch (error) {
            const errorMessage = error.response?.data?.detail || error.message;
            
            // Verificar se é erro de Evolution API não configurada
            if (errorMessage.includes('Evolution API não configurada')) {
                toast({
                    title: "⚠️ Evolution API Não Configurada",
                    description: (
                        <div className="space-y-2">
                            <p>A Evolution API ainda não foi configurada pelo administrador.</p>
                            <p className="text-sm text-muted-foreground">
                                O administrador precisa acessar <strong>Configurações → Evolution API</strong> e configurar a integração.
                            </p>
                        </div>
                    ),
                    variant: "destructive",
                });
            } else {
                toast({
                    title: "❌ Erro ao Criar Conexão",
                    description: errorMessage,
                    variant: "destructive",
                });
            }
        } finally {
            setCriandoConexao(false);
        }
    };

    const iniciarVerificacaoStatus = (conexaoId) => {
        const interval = setInterval(async () => {
            try {
                const response = await whatsappAPI.verificarStatus(conexaoId);
                
                if (response.data.status === 'conectado') {
                    clearInterval(interval);
                    await carregarConexoes();
                    toast({
                        title: "✅ WhatsApp Conectado!",
                        description: "Seu WhatsApp foi conectado com sucesso e está pronto para uso.",
                        variant: "default",
                    });
                }
            } catch (error) {
                console.error('Erro ao verificar status:', error);
            }
        }, 5000); // Verificar a cada 5 segundos
        
        // Parar após 2 minutos
        setTimeout(() => clearInterval(interval), 120000);
    };

    const atualizarQRCode = async (conexaoId) => {
        try {
            const response = await whatsappAPI.obterQRCode(conexaoId);
            const conexaoAtualizada = conexoes.map(c => 
                c.id === conexaoId ? {...c, qr_code: response.data.qr_code} : c
            );
            setConexoes(conexaoAtualizada);
            toast({
                title: "🔄 QR Code Atualizado",
                description: "O QR Code foi atualizado. Escaneie novamente com seu WhatsApp.",
                variant: "default",
            });
        } catch (error) {
            toast({
                title: "❌ Erro ao Atualizar QR Code",
                description: error.response?.data?.detail || "Não foi possível atualizar o QR Code.",
                variant: "destructive",
            });
        }
    };

    const deletarConexao = async (conexaoId) => {
        if (!window.confirm('Deseja realmente remover esta conexão?')) return;
        
        try {
            await whatsappAPI.deletarConexao(conexaoId);
            await carregarConexoes();
            toast({
                title: "🗑️ Conexão Removida",
                description: "A conexão WhatsApp foi removida com sucesso.",
                variant: "default",
            });
        } catch (error) {
            toast({
                title: "❌ Erro ao Deletar",
                description: error.response?.data?.detail || "Não foi possível remover a conexão.",
                variant: "destructive",
            });
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'conectado':
                return <CheckCircle className="w-5 h-5 text-emerald-500" />;
            case 'qrcode':
                return <Clock className="w-5 h-5 text-blue-500" />;
            case 'desconectado':
                return <XCircle className="w-5 h-5 text-red-500" />;
            default:
                return <Clock className="w-5 h-5 text-gray-500" />;
        }
    };

    const getStatusLabel = (status) => {
        const labels = {
            'conectado': 'Conectado',
            'qrcode': 'Aguardando QR Code',
            'desconectado': 'Desconectado',
            'erro': 'Erro'
        };
        return labels[status] || status;
    };

    return (
        <Layout>
            <div className="container mx-auto px-4 py-8">
                <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                                <Smartphone className="w-8 h-8 text-primary" />
                                WhatsApp
                            </h1>
                            <p className="text-muted-foreground mt-2">
                                Conecte seu WhatsApp e envie mensagens automáticas
                            </p>
                        </div>
                        <Button
                            onClick={criarNovaConexao}
                            disabled={criandoConexao || conexoes.some(c => c.status === 'qrcode')}
                        >
                            {criandoConexao ? 'Criando...' : '+ Nova Conexão'}
                        </Button>
                    </div>

                    {/* Banner de Aviso - Evolution API não configurada */}
                    {evolutionConfigured === false && (
                        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6">
                            <div className="flex items-start gap-4">
                                <AlertCircle className="w-6 h-6 text-yellow-500 flex-shrink-0 mt-0.5" />
                                <div className="flex-1">
                                    <h3 className="text-lg font-semibold text-yellow-500 mb-2">
                                        ⚠️ Evolution API Não Configurada
                                    </h3>
                                    <p className="text-sm text-foreground mb-3">
                                        A integração com WhatsApp ainda não foi configurada pelo administrador do sistema.
                                    </p>
                                    <div className="bg-background/50 rounded-lg p-3 text-sm">
                                        <p className="font-medium text-foreground mb-2">📋 Instruções para o Administrador:</p>
                                        <ol className="list-decimal list-inside space-y-1 text-muted-foreground ml-2">
                                            <li>Acesse <strong className="text-foreground">Configurações</strong></li>
                                            <li>Clique na aba <strong className="text-foreground">Evolution API</strong></li>
                                            <li>Configure a URL da API e a API Key</li>
                                            <li>Habilite a integração e salve</li>
                                        </ol>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}


                    {/* Lista de Conexões */}
                    {loading ? (
                        <div className="text-center py-12">Carregando...</div>
                    ) : conexoes.length === 0 ? (
                        <div className="bg-card rounded-xl border border-border p-12 text-center">
                            <Smartphone className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                            <h3 className="text-xl font-semibold text-foreground mb-2">
                                Nenhuma conexão WhatsApp
                            </h3>
                            <p className="text-muted-foreground mb-6">
                                Conecte seu WhatsApp para começar a enviar mensagens
                            </p>
                            <Button onClick={criarNovaConexao}>
                                Conectar WhatsApp
                            </Button>
                        </div>
                    ) : (
                        <div className="grid gap-6">
                            {conexoes.map((conexao) => (
                                <div key={conexao.id} 
                                     className="bg-card rounded-xl border border-border p-6">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start gap-4 flex-1">
                                            {/* Status Icon */}
                                            <div className="mt-1">
                                                {getStatusIcon(conexao.status)}
                                            </div>
                                            
                                            {/* Info */}
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <h3 className="text-lg font-semibold text-foreground">
                                                        {conexao.numero_telefone || 'WhatsApp'}
                                                    </h3>
                                                    <span className={`text-xs px-2 py-1 rounded-full ${
                                                        conexao.status === 'conectado' 
                                                            ? 'bg-emerald-500/20 text-emerald-500' 
                                                            : conexao.status === 'qrcode'
                                                            ? 'bg-blue-500/20 text-blue-500'
                                                            : 'bg-red-500/20 text-red-500'
                                                    }`}>
                                                        {getStatusLabel(conexao.status)}
                                                    </span>
                                                </div>
                                                
                                                <p className="text-sm text-muted-foreground">
                                                    Instância: {conexao.instance_name}
                                                </p>
                                                
                                                {conexao.data_conexao && (
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        Conectado em: {new Date(conexao.data_conexao).toLocaleString('pt-BR')}
                                                    </p>
                                                )}
                                                
                                                {/* QR Code */}
                                                {conexao.status === 'qrcode' && conexao.qr_code && (
                                                    <div className="mt-4 p-4 bg-white rounded-lg inline-block">
                                                        <img 
                                                            src={conexao.qr_code} 
                                                            alt="QR Code WhatsApp" 
                                                            className="w-[200px] h-[200px]"
                                                        />
                                                        <p className="text-xs text-center mt-2 text-gray-600">
                                                            Escaneie com seu WhatsApp
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        
                                        {/* Actions */}
                                        <div className="flex gap-2">
                                            {conexao.status === 'qrcode' && (
                                                <button
                                                    onClick={() => atualizarQRCode(conexao.id)}
                                                    className="p-2 hover:bg-muted rounded-lg transition"
                                                    title="Atualizar QR Code"
                                                >
                                                    <RefreshCw className="w-5 h-5" />
                                                </button>
                                            )}
                                            <button
                                                onClick={() => deletarConexao(conexao.id)}
                                                className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg transition"
                                                title="Remover"
                                            >
                                                <Trash2 className="w-5 h-5" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default WhatsAppConfig;