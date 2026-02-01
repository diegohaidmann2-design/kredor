import axios from 'axios';
import { BACKEND_URL } from './api';

const API = `${BACKEND_URL}/api`;

export const equipeAPI = {
    // Convidar novo membro
    convidarMembro: async (dados) => {
        const response = await axios.post(`${API}/equipe/convidar`, dados);
        return response.data;
    },

    // Listar membros da equipe
    listarEquipe: async () => {
        const response = await axios.get(`${API}/equipe`);
        return response.data;
    },

    // Remover membro (desativar)
    removerMembro: async (id) => {
        const response = await axios.delete(`${API}/equipe/${id}`);
        return response.data;
    },

    // Atualizar permissões
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
