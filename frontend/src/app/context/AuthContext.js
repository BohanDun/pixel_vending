"use client"

import { createContext, useEffect, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        localStorage.removeItem('token');
        const token = sessionStorage.getItem('token');

        if (token) {
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            setUser({ access_token: token });
        }

        setLoading(false);
    }, []);

    const login = async (username, password) => {
        try{
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);
            const response = await axios.post('http://localhost:8000/auth/token', formData,{
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
           });
           axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
           sessionStorage.setItem('token', response.data.access_token);
           setUser(response.data);
           router.push('/');
        } catch(error){
            console.log('Login Failed:', error);
            throw error;
        }
    };

    const logout = () => {
         setUser(null);
         localStorage.removeItem('token');
         sessionStorage.removeItem('token');
         delete axios.defaults.headers.common['Authorization'];
         router.push('/login')
    };

    return (
        <AuthContext.Provider value={{user, loading, login, logout}}>
            {children}
        </AuthContext.Provider>
    );
};

    
    export default AuthContext;
