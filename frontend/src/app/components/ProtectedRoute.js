"use client"

import { useContext, useEffect } from "react";
import { useRouter } from "next/navigation";
import AuthContext from "../context/AuthContext";

const ProtectedRoute = ({ children }) => {
    const { user, loading } = useContext(AuthContext);
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push('/login');
        }
    }, [loading, user, router]);

    if (loading) {
        return (
            <div className="app-loading" role="status" aria-live="polite">
                <span className="brand-mark" aria-hidden="true">
                    <i /><i /><i />
                </span>
                <div>
                    <strong>Pixel Vend</strong>
                    <small>Preparing your store…</small>
                </div>
            </div>
        );
    }

    return user ? children : null;
};

export default ProtectedRoute;
