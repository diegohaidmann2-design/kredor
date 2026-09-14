import axios from 'axios';
import { BACKEND_URL } from './api';

const API = `${BACKEND_URL}/api`;

// Diferente dos outros módulos de api/, aqui cada função devolve response.data — as telas de
// equipe consomem o corpo direto. O interceptor de Authorization é o de api/api.js (axios global).
export const equipeAPI = {
    // Convidar novo membro (ou cadastrar com senha definida na hora)
    convidarMembro: async (dados) => {
        const response = await axios.post(`${API}/equipe/convidar`, dados);
        return response.data;
    },

    // Listar membros, limites do plano e as permissões que o servidor reconhece
    listarEquipe: async () => {
        const response = await axios.get(`${API}/equipe`);
        return response.data;
    },

    // Remover (cancela o convite pendente; desativa quem já entrou)
    removerMembro: async (id) => {
        const response = await axios.delete(`${API}/equipe/${id}`);
        return response.data;
    },

    // Devolver acesso a um membro desativado
    reativarMembro: async (id) => {
        const response = await axios.post(`${API}/equipe/${id}/reativar`);
        return response.data;
    },

    // Gera um token novo e reenvia o email; invalida o convite anterior
    reenviarConvite: async (id) => {
        const response = await axios.post(`${API}/equipe/${id}/reenviar-convite`);
        return response.data;
    },

    // Substituir as permissões de um membro
    atualizarPermissoes: async (id, dados) => {
        const response = await axios.put(`${API}/equipe/${id}/permissoes`, dados);
        return response.data;
    },

    // Aceitar Convite (Público)
    aceitarConvite: async (dados) => {
        const response = await axios.post(`${API}/equipe/aceitar-convite`, dados);
        return response.data;
    }
};

export default equipeAPI;
