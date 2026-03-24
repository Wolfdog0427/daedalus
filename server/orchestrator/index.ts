import express from "express";
import { daedalusRouter } from "./daedalusRouter";

export const createOrchestratorApp = () => {
  const app = express();
  app.use(express.json());
  app.use("/daedalus", daedalusRouter);
  return app;
};
