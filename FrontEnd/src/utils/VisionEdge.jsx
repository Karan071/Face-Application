    import React from 'react';
    import visionEdge from '../assets/face-icon.gif'
    import { Link } from 'react-router-dom';

    const Navbar = ({ buttonText, onButtonClick }) => {
    return (
        <div className="flex justify items-center px-8 py-4 bg-white">
        {/* Logo and Title */}
            <Link to = "/">  
            <div className="flex items-center">
                <img src={visionEdge} alt="Logo" className="h-10 w-10 mr-2" />
                <p className="text-3xl font-bold bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 inline-block text-transparent bg-clip-text">
                VisionEdge
                </p>
            </div>
            </Link>
        
            {/* Button */}
            {/* <button
                type="button"
                onClick={onButtonClick}
                className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-5 py-2.5"
            >
                {buttonText}
            </button> */}
        </div>
    );
    };

    export default Navbar;
