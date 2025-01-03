import React from "react";
import VisionEdge from "../utils/VisionEdge";
import { FaCheckCircle } from "react-icons/fa";
import imgAsset from "../assets/Robot.png"
import { Link } from "react-router-dom";

const CheckIn = () => {
  return (
    <div className="h-screen flex flex-col bg-gray-50 font-poppins">
      <div className="w-full">
        <VisionEdge /> 
      </div>

      <div className="flex-1 flex flex-col items-center mt-6">
        <p className="text-4xl font-thin text-gray-700 mb-4 mt-11">
          Check In Successful
        </p>
        <div className="mt-9">
          <div className="flex flex-col items-center justify-center p-8 border-2 border-green-600 bg-green-50 rounded-lg shadow-lg w-96">
          
                {/* icon */}
                <FaCheckCircle className="text-green-600" size={72} />
                
                {/* Heading */}
                <h2 className="text-3xl font-bold text-gray-800 mt-4">Marked Successful !</h2>

                {/* image example*/}
                <div>
                  <img src={imgAsset} alt="Employee Image" />
                </div>
          
          
                <p className="text-gray-700 text-center mt-3">{`Karan Chourasia is successfully check-in`}</p>

                
                {/* Button */}
                <Link to="/main-page">
                <button
                  // onClick={onContinue}
                  className="mt-6 px-5 py-2 border-2 border-green-600 text-green-600 font-semibold rounded-lg hover:bg-green-600 hover:text-white transition duration-300 ease-in-out transform hover:scale-105"
                >
                  CONTINUE
                </button>
                </Link>
              </div>
        </div>
      </div>
    </div>
  );
};

export default CheckIn;
