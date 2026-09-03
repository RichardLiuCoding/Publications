"""Hand coding of the 68 operator prompts in chat_history_260814.

Scheme (primary function; secondary allowed). Coded by the agent that is also the
subject of the study - the scheme and the raw turns are both in the repo so the
coding can be independently redone.

  ROLE      sets or reaffirms the division of labour / working protocol
  LIT       supplies literature and asks for integration
  CHALLENGE questions a claim or premise without asserting the answer
  CORRECT   asserts the model is wrong on a matter of fact or interpretation
  SELFCORR  reports the operator's own error, invalidating data or a diagnosis
  PHYSICS   supplies domain knowledge, a physical constraint, or an own hypothesis
  DESIGN    proposes or modifies an experiment / trajectory / geometry
  ASKPLAN   asks the model to produce a plan or protocol
  SPECMETH  specifies how something must be measured, analysed or reported
  CONSTR    instrument, sample or logistics limit that bounds the design space
  DATA      returns instrument results for analysis
  TOOLING   asks for code, visualisation, or a usability fix
  DELIV     asks for a document, figure set, or export
"""
CODES = {
      1: ("ROLE",     None,       "read five theory docs, get ready to measure together"),
     28: ("ROLE",     None,       "I don't need you to run the codes ... I will execute"),
     32: ("TOOLING",  None,       "Igor text too small over remote desktop"),
     34: ("TOOLING",  None,       "SetIgorOption syntax error"),
     36: ("TOOLING",  None,       "It's 6.38"),
     38: ("LIT",      "ASKPLAN",  "Vasudevan PDF + refine understanding and plan"),
     62: ("CHALLENGE",None,       "were they able to re-configure it with trajectory writing path?"),
     64: ("CHALLENGE",None,       "re-configure its direction with trajectory writing path?"),
     66: ("CORRECT",  None,       "No, you're wrong ... only thing changed is the phase"),
     71: ("CORRECT",  "LIT",      "No, you're wrong (+ pasted Fig 2c)"),
     73: ("ASKPLAN",  None,       "propose a concrete experimental plan I can perform"),
     75: ("DESIGN",   "TOOLING",  "here is how I typically run trajectory lithos - modify for session 1"),
     77: ("CHALLENGE","TOOLING",  "Does this look correct to you? (+ preview image)"),
     79: ("CONSTR",   None,       "changed the voltage to 8 V"),
     81: ("DATA",     "CONSTR",   "back to 6 V; two VDART runs to avoid resonance degradation"),
    100: ("CHALLENGE","ASKPLAN",  "stick to the session 2 plan or change it?"),
    102: ("CONSTR",   "DESIGN",   "move to a new location, 6 um away?"),
    104: ("TOOLING",  "SPECMETH", "how to visualise all trajectories to make sure they are correct"),
    106: ("DESIGN",   None,       "increase the number of angles to 9"),
    108: ("TOOLING",  None,       "how to load this list of trajectories"),
    110: ("CORRECT",  "TOOLING",  "No, it's not working. Just write all into a single file"),
    112: ("DATA",     "DESIGN",   "results loaded; changed panel scan size to 1.25 um"),
    122: ("CONSTR",   None,       "no way to rotate the sample and relocate"),
    126: ("CONSTR",   None,       "cannot physically rotate the sample now"),
    128: ("DESIGN",   None,       "to better use space, I made the following changes"),
    130: ("CONSTR",   "DATA",     "measurement started; changed R to 1.75"),
    132: ("SELFCORR", None,       "don't trust the B site - I forgot to turn off the -8 V bias"),
    142: ("DESIGN",   None,       "move to session 4; nothing new from session 3"),
    144: ("CHALLENGE","ASKPLAN",  "session 5 or 6? increase amplitude or AC+DC?"),
    146: ("DELIV",    "SPECMETH", "summarize into a word doc using the real data"),
    166: ("SPECMETH", None,       "where are the figures? real-data figures, not tables"),
    201: ("SPECMETH", None,       "follow the figure making skill for all figures"),
    253: ("DATA",     "CHALLENGE","diamond probe; is the lateral domain aligned by the normal scan?"),
    270: ("DATA",     None,       "I just took an 8 um size here"),
    278: ("DESIGN",   "PHYSICS",  "directional square scan; we never fully pole the OP domain"),
    280: ("DATA",     "CHALLENGE","what does the rotation do? did you find anything else?"),
    297: ("DELIV",    "SPECMETH", "summary doc from the notebook, same figure skill"),
    330: ("PHYSICS",  "DESIGN",   "here is my new hypothesis (3 parts) + 500 nm test proposal"),
    332: ("CONSTR",   None,       "fresh area or continue in the previous area?"),
    334: ("DESIGN",   None,       "design a W x H square trajectory at a specified angle"),
    336: ("CORRECT",  None,       "why is the centre of trajectory so off?"),
    340: ("DELIV",    "ASKPLAN",  "digest session 3, summarise, suggest what next"),
    348: ("CHALLENGE","ASKPLAN",  "I seem to have switched them. How did I do it? How to make it reliable?"),
    374: ("ASKPLAN",  "TOOLING",  "lay out the steering test in detail and give me codes"),
    376: ("SELFCORR", "CONSTR",   "alignment was my fault - I forgot to load the new txt"),
    378: ("DELIV",    None,       "summary doc from both notebooks"),
    381: ("PHYSICS",  "DELIV",    "hard to overcome the large-scale superdomain potential; use point-pulse?"),
    480: ("ROLE",     "DESIGN",   "interactive notebook protocol + three hypotheses to examine"),
    518: ("CONSTR",   None,       "LDART resonance is 620 kHz"),
    523: ("CONSTR",   None,       "write voltage max +/- 10 V"),
    531: ("DATA",     "CONSTR",   "step 0 done; deflection drift; setpoint guidance"),
    547: ("CHALLENGE",None,       "why do you say it's already-poled? is it grown poled?"),
    555: ("SPECMETH", None,       "explain how you extract the phase and quantify directionality"),
    574: ("SPECMETH", None,       "Canny vs FFT - which is more immune to noise?"),
    588: ("SPECMETH", None,       "does it change direction at the same location? how to quantify?"),
    598: ("SPECMETH", "CONSTR",   "check the quality of the contact tuning"),
    609: ("TOOLING",  None,       "which part do I need to re-run?"),
    618: ("DESIGN",   None,       "rework step 0 to the session-5 geometry"),
    628: ("TOOLING",  None,       "there is no cell number in my notebook"),
    638: ("DATA",     "DELIV",    "new results updated; summarise and change next steps"),
    653: ("CHALLENGE",None,       "how to rule out probe degradation or a bad sample area?"),
    662: ("CONSTR",   "DESIGN",   "10 h gap; skip prob.1/2; change probe after R1"),
    673: ("SELFCORR", "PHYSICS",  "no, wait - the probe was wrapped by junk and the pulses cleaned it"),
    685: ("CONSTR",   None,       "which step is good to replace the probe?"),
    691: ("DATA",     None,       "gate 1 and 2 finished - read the results"),
    697: ("PHYSICS",  "CORRECT",  "we should have used opposite/alternating sign - we already know we must flip OP"),
    705: ("SPECMETH", None,       "write a findings .md, rate the credibility of each conclusion"),
    715: ("DELIV",    None,       "export this chat history to json and md"),
}
