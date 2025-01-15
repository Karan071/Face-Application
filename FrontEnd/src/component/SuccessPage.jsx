import React from "react";
import { useLocation, Link } from "react-router-dom";
import { FaCheckCircle } from "react-icons/fa";

const SuccessPage = () => {
  const location = useLocation();
  const { name, similarity, photo } = location.state || {};

  return (
    <div className="min-h-screen flex items-center justify-center font-mono">
      <div className="flex flex-col items-center font-mono p-8 max-w-lgborder-2 border-green-600 bg-green-50 rounded-lg shadow-lg  ">
        <h1 className="text-4xl font-semibold text-gray-800 mb-6">
          Check-In Successful!
        </h1>

        <div className="mb-6">
          <FaCheckCircle className="text-green-500" size={72} />
        </div>

        {/* <h2 className="text-3xl font-bold text-gray-800 mt-4">Marked Successful !</h2> */}
     
        <img
          src={photo}
          alt="Checked-in person"
          className="rounded-lg mb-6 w-full max-w-sm object-cover"
        />

        <div className="text-center">
          <p className="text-2xl font-bold text-gray-700 mb-2">
            Welcome, {name}!
          </p>
          <p className="text-gray-600 mb-6">
            Match Similarity: {similarity}%
          </p>

          <Link
            to="/dashboard"
            className="mt-6 px-5 py-2 border-2 border-green-600 text-green-600 font-semibold rounded-lg hover:bg-green-600 hover:text-white transition duration-300 ease-in-out transform hover:scale-105"
          >
            Back to Check-In
          </Link>
        </div>
      </div>
    </div>
  );
};

export default SuccessPage;
