import React from 'react';
import { Link } from 'react-router-dom';

const InternalServer = () => {
    return (
        <div className="w-full h-screen flex flex-col justify-center items-center bg-gray-50 px-6">
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 inline-block text-transparent bg-clip-text mb-5">Something Went Wrong</h1>
            <h3 className="text-xl md:text-2xl font-semibold text-gray-600 mb-2">
                500 - Internal Server Error
            </h3>
            <p className="text-sm md:text-base text-gray-500 mb-6 text-center max-w-md font-thin">
                We’re sorry! Something went wrong on our end. Please try again.
            </p>
            <Link>
                <button
                    className="mt-3 text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-6 py-3 transition-all duration-200 ease-in-out"
                >
                    Back to Home Page
                </button>
            </Link>
        </div>
    );
};

export default InternalServer;
