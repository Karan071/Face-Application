import React from "react";

const HoverButton = ({
  text,
  buttonColor,
  hoverColor,
  textColor,
  width,
  height,
}) => {
  return (
    <button
      className={`border hover:scale-95 duration-300 relative group cursor-pointer ${textColor} overflow-hidden ${height} ${width} rounded-md ${buttonColor} p-2 flex justify-center items-center font-extrabold`}
    >
      <div
        className={`absolute right-32 -top-4 group-hover:top-1 group-hover:right-2 z-10 w-40 h-40 rounded-full group-hover:scale-150 duration-500 ${hoverColor[0]}`}
      ></div>
      <div
        className={`absolute right-2 -top-4 group-hover:top-1 group-hover:right-2 z-10 w-32 h-32 rounded-full group-hover:scale-150 duration-500 ${hoverColor[1]}`}
      ></div>
      <div
        className={`absolute -right-12 top-4 group-hover:top-1 group-hover:right-2 z-10 w-24 h-24 rounded-full group-hover:scale-150 duration-500 ${hoverColor[2]}`}
      ></div>
      <div
        className={`absolute right-20 -top-4 group-hover:top-1 group-hover:right-2 z-10 w-16 h-16 rounded-full group-hover:scale-150 duration-500 ${hoverColor[3]}`}
      ></div>
      <p className="z-10">{text}</p>
    </button>
  );
};

HoverButton.defaultProps = {
  text: "See More",
  buttonColor: "bg-sky-200",
  hoverColor: ["bg-sky-900", "bg-sky-800", "bg-sky-700", "bg-sky-600"],
  textColor: "text-sky-50",
  width: "w-64",
  height: "h-16",
};

export default HoverButton;
