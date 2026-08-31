import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const fetchRecords = (status) =>
  axios.get(`${API}/records`, { params: status ? { status } : {} }).then((r) => r.data);
export const fetchRecord = (id) => axios.get(`${API}/records/${id}`).then((r) => r.data);
export const fetchParcels = () => axios.get(`${API}/parcels`).then((r) => r.data);
export const fetchSamples = () => axios.get(`${API}/samples`).then((r) => r.data);
export const processSample = (name) => axios.post(`${API}/samples/${name}/process`).then((r) => r.data);
export const uploadDocument = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return axios.post(`${API}/upload`, fd).then((r) => r.data);
};
export const decideRecord = (id, action) =>
  axios.post(`${API}/records/${id}/decision`, { action }).then((r) => r.data);
export const reseed = () => axios.post(`${API}/seed`).then((r) => r.data);
