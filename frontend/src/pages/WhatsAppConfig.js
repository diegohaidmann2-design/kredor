import React, { useState, useEffect, useCallback, useRef } from 'react';
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
    const pollingIntervalsRef = useRef({});
    const { toast } = useToast();

    const carregarConexoes = useCallback(async () => {
        try {
            const response = await whatsappAPI.listarConexoes();
            setConexoes(response.data.items);
        } catch (error) {
            console.error('Erro ao carregar conexões:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    const atualizarQRCode = useCallback(async (conexaoId) => {
        try {
            const response = await whatsappAPI.obterQRCode(conexaoId);
            const conexaoAtualizada = conexoes.map(c => 
                c.id === conexaoId ? {...c, qr_code: response.data.qr_code} : c
            );
            setConexoes(conexaoAtualizada);
            // Não mostrar toast na atualização automática silenciosa
            // toast já será mostrado apenas no click manual do botão
        } catch (error) {
            console.error('Erro ao atualizar QR Code:', error);
        }
    }, [conexoes]);

    const iniciarVerificacaoStatus = useCallback((conexaoId) => {
        // Se já existe polling para esta conexão, não criar outro
        if (pollingIntervalsRef.current[conexaoId]) {
            return;
        }
        
        const interval = setInterval(async () => {
            try {
                const response = await whatsappAPI.verificarStatus(conexaoId);
                
                if (response.data.status === 'conectado') {
                    clearInterval(interval);
                    delete pollingIntervalsRef.current[conexaoId];
                    await carregarConexoes();
                    toast({
                        title: "✅ WhatsApp Conectado!",
                        description: "Seu WhatsApp foi conectado com sucesso e está pronto para uso.",
                        variant: "default",
                    });
                } else {
                    // Atualizar apenas esta conexão
                    await carregarConexoes();
                }
            } catch (error) {
                console.error('Erro ao verificar status:', error);
            }
        }, 5000);
        
        // Atualizar QR Code automaticamente a cada 45 segundos
        const qrRefreshInterval = setInterval(async () => {
            try {
                await atualizarQRCode(conexaoId);
            } catch (error) {
                console.error('Erro ao atualizar QR Code automaticamente:', error);
            }
        }, 45000); // 45 segundos
        
        // Armazenar os intervalos
        pollingIntervalsRef.current[conexaoId] = interval;
        pollingIntervalsRef.current[`${conexaoId}_qr`] = qrRefreshInterval;
        
        // Parar após 3 minutos
        setTimeout(() => {
            if (pollingIntervalsRef.current[conexaoId]) {
                clearInterval(pollingIntervalsRef.current[conexaoId]);
                delete pollingIntervalsRef.current[conexaoId];
            }
            if (pollingIntervalsRef.current[`${conexaoId}_qr`]) {
                clearInterval(pollingIntervalsRef.current[`${conexaoId}_qr`]);
                delete pollingIntervalsRef.current[`${conexaoId}_qr`];
            }
        }, 180000);
    }, [carregarConexoes, toast]);

    useEffect(() => {
        carregarConexoes();
        verificarEvolutionAPI();
        
        // Polling geral para atualizar lista a cada 10 segundos
        const intervalGeral = setInterval(() => {
            carregarConexoes();
        }, 10000);
        
        // Limpar intervalo ao desmontar
        return () => {
            clearInterval(intervalGeral);
            // Limpar todos os intervalos de polling
            Object.values(pollingIntervalsRef.current).forEach(interval => clearInterval(interval));
            pollingIntervalsRef.current = {};
        };
    }, [carregarConexoes]);

    // Iniciar polling para conexões com status "qrcode"
    useEffect(() => {
        conexoes.forEach(conexao => {
            if (conexao.status === 'qrcode' && !pollingIntervalsRef.current[conexao.id]) {
                iniciarVerificacaoStatus(conexao.id);
            }
        });
    }, [conexoes, iniciarVerificacaoStatus]);

    const verificarEvolutionAPI = async () => {
        try {
            const response = await whatsappAPI.obterConfigEvolution();
            setEvolutionConfigured(response.data.habilitado && response.data.api_url && response.data.api_key);
        } catch (error) {
            setEvolutionConfigured(false);
        }
    };

    const criarNovaConexao = async () => {
        try {
            setCriandoConexao(true);
            const response = await whatsappAPI.criarConexao();
            
            // Aguardar 1.5s para garantir que o QR Code está pronto
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            await carregarConexoes();
            
            // Iniciar polling de status
            iniciarVerificacaoStatus(response.data.id);
            
            toast({
                title: "🔗 Conexão Criada!",
                description: "Escaneie o QR Code para conectar seu WhatsApp.",
                variant: "default",
            });
        } catch (error) {
            const errorMessage = error.response?.data?.detail || error.message;
            
            // Verificar se é erro de Evolution API não configurada
            if (errorMessage.includes('Evolution API não configurada')) {
                toast({
                    title: "⚠️ WhatsApp Não Configurado",
                    description: "A integração com WhatsApp ainda não foi configurada. Entre em contato com o administrador.",
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

    const atualizarQRCodeManual = async (conexaoId) => {
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
                                        ⚠️ WhatsApp Não Configurado
                                    </h3>
                                    <p className="text-foreground">
                                        A integração com WhatsApp ainda não foi configurada. 
                                        Entre em contato com o administrador do sistema.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}


                    {/* Lista de Conexões */}
                    {loading ? (
                        <div className="text-center py-12">Carregando...</div>
                    ) : (
                        <>
                            {/* Loading Card - Criando Conexão */}
                            {criandoConexao && (
                                <div className="bg-card rounded-xl border border-border p-8 animate-in fade-in duration-500">
                                    <div className="flex flex-col items-center justify-center gap-6">
                                        {/* Animated WhatsApp Icon */}
                                        <div className="relative">
                                            <div className="absolute inset-0 bg-emerald-500/20 rounded-full animate-ping"></div>
                                            <div className="relative bg-emerald-500/10 p-6 rounded-full">
                                                <Smartphone className="w-12 h-12 text-emerald-500 animate-pulse" />
                                            </div>
                                        </div>
                                        
                                        {/* Loading Text */}
                                        <div className="text-center space-y-2">
                                            <h3 className="text-lg font-semibold text-foreground">
                                                Criando sua conexão WhatsApp...
                                            </h3>
                                            <p className="text-sm text-muted-foreground">
                                                Aguarde enquanto geramos seu QR Code
                                            </p>
                                        </div>
                                        
                                        {/* Loading Dots */}
                                        <div className="flex gap-2">
                                            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                                            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                                            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            
                            {conexoes.length === 0 && !criandoConexao ? (
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
                            ) : conexoes.length > 0 ? (
                        <div className="grid gap-6">
                            {conexoes.map((conexao) => (
                                <div key={conexao.id} 
                                     className="bg-card rounded-xl border border-border p-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
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
                                                    <div className="mt-4 animate-in fade-in zoom-in-95 duration-700">
                                                        <div className="flex items-center gap-2 mb-3">
                                                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                                            <p className="text-sm text-blue-500 font-medium">
                                                                Aguardando conexão... (atualização automática)
                                                            </p>
                                                        </div>
                                                        <div className="p-4 bg-white rounded-lg inline-block shadow-lg transform hover:scale-105 transition-transform duration-300">
                                                            <div className="relative">
                                                                {/* Border animado */}
                                                                <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg blur opacity-25 animate-pulse"></div>
                                                                <div className="relative bg-white p-2 rounded-lg">
                                                                    <img 
                                                                        src={conexao.qr_code} 
                                                                        alt="QR Code WhatsApp" 
                                                                        className="w-[200px] h-[200px] rounded"
                                                                    />
                                                                </div>
                                                            </div>
                                                            <p className="text-xs text-center mt-3 text-gray-600 font-medium">
                                                                📱 Escaneie com seu WhatsApp
                                                            </p>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        
                                        {/* Actions */}
                                        <div className="flex gap-2">
                                            {conexao.status === 'qrcode' && (
                                                <button
                                                    onClick={() => atualizarQRCodeManual(conexao.id)}
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
                            ) : null}
                        </>
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default WhatsAppConfig;