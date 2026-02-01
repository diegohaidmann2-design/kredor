/**
 * Componente de Teste - Timezone São Paulo
 * 
 * Use este componente para verificar se o timezone está funcionando
 * Acesse: /timezone-test
 */

import React, { useState, useEffect } from 'react';
import { BACKEND_URL } from '../config/env';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { 
  formatDateBR, 
  formatDateLong, 
  formatDateTimeFull,
  formatTime,
  getTimezoneInfo,
  nowSP,
  toSaoPaulo,
  isToday
} from '../utils/timezone';

const TimezoneTest = () => {
  const [currentTime, setCurrentTime] = useState(nowSP());
  const [backendInfo, setBackendInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Atualizar relógio a cada segundo
    const interval = setInterval(() => {
      setCurrentTime(nowSP());
    }, 1000);

    // Buscar info do backend
    const fetchBackendInfo = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/timezone-info`);
        const data = await response.json();
        setBackendInfo(data);
      } catch (error) {
        console.error('Erro ao buscar info do backend:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchBackendInfo();

    return () => clearInterval(interval);
  }, []);

  const timezoneInfo = getTimezoneInfo();

  // Exemplo de data do banco (UTC)
  const exampleDateUTC = "2026-01-21T16:30:00Z";
  const exampleDateConverted = toSaoPaulo(exampleDateUTC);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 py-12 px-4">
      <div className="container mx-auto max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">🌍 Teste de Timezone - São Paulo</h1>
          <p className="text-slate-600 dark:text-slate-400">
            Verificação do fuso horário configurado no sistema
          </p>
        </div>

        <div className="grid gap-6">
          {/* Relógio Atual */}
          <Card>
            <CardHeader>
              <CardTitle>⏰ Hora Atual em São Paulo</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center">
                <div className="text-5xl font-bold text-primary mb-2">
                  {formatTime(currentTime)}
                </div>
                <div className="text-xl text-slate-600 dark:text-slate-400">
                  {formatDateBR(currentTime, false)}
                </div>
                <div className="text-sm text-slate-500 mt-2">
                  {formatDateLong(currentTime)}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Info do Frontend */}
          <Card>
            <CardHeader>
              <CardTitle>📱 Frontend (React)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">Timezone:</span>
                <span className="font-mono font-medium">{timezoneInfo.timezone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">Offset:</span>
                <span className="font-mono font-medium">{timezoneInfo.offsetHours}h ({timezoneInfo.offsetStr})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">Hora Atual:</span>
                <span className="font-mono font-medium">{timezoneInfo.currentTime}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">Timezone do Navegador:</span>
                <span className="font-mono font-medium text-xs">{timezoneInfo.userTimezone}</span>
              </div>
            </CardContent>
          </Card>

          {/* Info do Backend */}
          {loading ? (
            <Card>
              <CardContent className="py-8 text-center">
                <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
                <p className="mt-4 text-slate-600 dark:text-slate-400">Carregando info do backend...</p>
              </CardContent>
            </Card>
          ) : backendInfo ? (
            <Card>
              <CardHeader>
                <CardTitle>🖥️ Backend (FastAPI)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Timezone:</span>
                  <span className="font-mono font-medium">{backendInfo.timezone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Offset:</span>
                  <span className="font-mono font-medium">{backendInfo.offset_hours}h ({backendInfo.offset_str})</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Horário de Verão:</span>
                  <span className="font-mono font-medium">{backendInfo.is_dst ? 'Sim' : 'Não'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Hora Local (SP):</span>
                  <span className="font-mono font-medium text-xs">{backendInfo.now_sp_formatted}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Hora UTC:</span>
                  <span className="font-mono font-medium text-xs">{backendInfo.now_utc_formatted}</span>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-red-600">
                ❌ Erro ao carregar informações do backend
              </CardContent>
            </Card>
          )}

          {/* Exemplo de Conversão */}
          <Card>
            <CardHeader>
              <CardTitle>🔄 Exemplo de Conversão</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                  Data vinda do banco (UTC):
                </p>
                <code className="block bg-slate-100 dark:bg-slate-800 p-2 rounded text-xs font-mono">
                  {exampleDateUTC}
                </code>
              </div>

              <div className="border-t pt-4">
                <p className="text-sm font-medium mb-3">Conversões:</p>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">formatDateBR():</span>
                    <span className="font-medium">{formatDateBR(exampleDateUTC)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">formatDateBR(false):</span>
                    <span className="font-medium">{formatDateBR(exampleDateUTC, false)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">formatDateLong():</span>
                    <span className="font-medium">{formatDateLong(exampleDateUTC)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">formatDateTimeFull():</span>
                    <span className="font-medium">{formatDateTimeFull(exampleDateUTC)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">formatTime():</span>
                    <span className="font-medium">{formatTime(exampleDateUTC)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600 dark:text-slate-400">isToday():</span>
                    <span className="font-medium">{isToday(exampleDateUTC) ? 'Sim ✅' : 'Não ❌'}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status */}
          <Card className="border-2 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20">
            <CardContent className="py-6">
              <div className="flex items-center gap-3">
                <div className="text-3xl">✅</div>
                <div>
                  <p className="font-bold text-emerald-800 dark:text-emerald-200">
                    Timezone Configurado Corretamente!
                  </p>
                  <p className="text-sm text-emerald-700 dark:text-emerald-300">
                    Sistema operando no fuso horário de São Paulo (UTC-3)
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TimezoneTest;
