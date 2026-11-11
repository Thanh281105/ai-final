# Task 1 (3.0 points): Local Search & Propositional Logic

**Description:** N-Queen problem  
**Source pages:** 1-2 of the assignment PDF

## Description

- Given a chess board with the size of N x N, students implement a solver to find a solution for placing N queens on the board without attacking pairs.
- Assign to each square on the board a logical variable in which if the variable holds the value True, the square contains a queen, and if the variable holds the value False, the square is empty.

## Requirements

### 1. (1.0 point)

Formulate the given problem as a Propositional Logic problem and introduce its relevant components. Discuss an algorithm for discovering the constraints that govern the placement of queens on the chessboard, and explain the procedure for converting these constraints into Conjunctive Normal Form (CNF) clauses.

### 2. (1.0 point)

Use the Glucose3 solver from the PySAT library to find a solution to the given problem and conduct experiments with increasing values of N, where N >= 4. For each value of N, report the total number of CNF clauses and the running time required by the solver.

### 3. (1.0 point)

Solve the problem using the Min-Conflicts algorithm introduced in Lecture 08 and propose a heuristic for selecting variables. Conduct experiments to evaluate the effectiveness of the proposed heuristic by comparing its performance with the standard Min-Conflicts approach.

## Notice

- Recommended editor: Visual Studio Code.
- The project must be designed and implemented following Object-Oriented Programming principles.
- The evaluation configurations: macOS 13.7.8 (Ventura) with an Intel Core i5 processor.
