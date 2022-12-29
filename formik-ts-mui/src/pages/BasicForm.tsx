import React, { useState } from "react";
import { useStyles } from "./styles";
//formik imports
import {
  Formik,
  FormikHelpers,
  FormikProps,
  Form,
  Field,
  FieldProps,
} from "formik";
import * as yup from "yup";

//import components
import { Button } from "@material-ui/core";
import TextFieldComponent from "../components/TextFieldComponent";
import SelectField from "../components/select-field";
import DatePickerField from "../components/date-picker-field";
import CheckboxField from "../components/checkbox-field";
import RadioButtonsGroup from "../components/radio-button";
import ValidationSchema from "./ValidationSchema";

//model
interface MyFormValues {
  firstName: string; //textfield
  age: number; //textfield
  gender: string; //selectField
  dateOfBirth: string; //datePicker
  englishSpeak: boolean; //checkbox
  englishRead: boolean; //checkbox
  englishWrite: boolean; //checkbox
  subscription: boolean; //radio button
  //nested data in array
  assetDetails: {
    assetName: string;
    assetId: string;
  }[];
}

const initialData: MyFormValues = {
  firstName: "Sanjoy Pator",
  age: 23,
  gender: "male",
  dateOfBirth: "1998-12-25",
  englishSpeak: false,
  englishRead: true,
  englishWrite: false,
  subscription: false,
  assetDetails: [
    {
      assetName: "ipad pro",
      assetId: "ls124",
    },
    {
      assetName: "macbook pro",
      assetId: "ms124",
    },
  ],
};

//input

//SELECT FIELD - DATA - gender selection options
const genderSelectOptions = [
  {
    value: "male",
    label: "Male",
  },
  {
    value: "female",
    label: "Female",
  },
  {
    value: "other",
    label: "Other",
  },
];

// Radio Group - subscriptionStatusOptions initial data
const subscriptionStatusOptions = [
  {
    value: true,
    label: "Active",
  },
  {
    value: false,
    label: "Inactive",
  },
];

// yup validation
const validationSchema = yup
  .object()
  .shape(ValidationSchema.BasicFormValidationSchema);

const BasicForm: React.FC = () => {
  const classes = useStyles();

  const [isEditable, setIsEditable] = useState(false);
  const [assetdataTemp, setAssetdataTemp] = useState(initialData.assetDetails);

  const handleSubmit = (val: any) => {
    if (isEditable) {
      console.log("vals", val);
      setAssetdataTemp(val.assetDetails);
    }
  };

  //add field dynamically
  let addFormFields = () => {
    console.log("assetdataTemp ", assetdataTemp);
    setAssetdataTemp([...assetdataTemp, { assetName: "", assetId: "" }]);
  };

  return (
    <div>
      <h3>Basic Form</h3>
      <div className={classes.mainContainer}>
        <Formik
          initialValues={initialData}
          validationSchema={validationSchema}
          onSubmit={(values, formikHelpers) => {
            // console.log("Subbmiting done: ", values);
            setIsEditable(!isEditable);
            formikHelpers.setSubmitting(false);
            handleSubmit(values);
          }}
        >
          {(formikProps: FormikProps<MyFormValues>) => (
            <Form noValidate autoComplete="off">
              <div>
                <div className={classes.innerDivStyle}>
                  Name :
                  {isEditable ? (
                    <TextFieldComponent
                      defaultProps={{
                        name: "firstName",
                        // label: "Name",
                        fullWidth: false,
                        placeholder: "Enter name",
                      }}
                    />
                  ) : (
                    <label htmlFor="firstName">
                      {formikProps.values.firstName}
                    </label>
                  )}
                </div>
                <div className={classes.innerDivStyle}>
                  Age :
                  {isEditable ? (
                    <TextFieldComponent
                      defaultProps={{
                        name: "age",
                        // label: "Name",
                        fullWidth: false,
                        placeholder: "Enter age",
                      }}
                    />
                  ) : (
                    <label htmlFor="age">{formikProps.values.age}</label>
                  )}
                </div>
                <div className={classes.innerDivStyle}>
                  <label htmlFor="gender">Gender : </label>

                  <SelectField
                    name={"gender"}
                    label={"Gender"}
                    data={genderSelectOptions}
                    isEditableProps={isEditable}
                  />
                </div>
                <div className={classes.innerDivStyle}>
                  <div>
                    <label
                      htmlFor="dateOfBirth"
                      style={{ marginRight: "20px" }}
                    >
                      Date Of Birth :{" "}
                    </label>
                  </div>
                  <div>
                    <DatePickerField
                      name={"dateOfBirth"}
                      format={"dd/MM/yy"}
                      value={formikProps.values.dateOfBirth}
                      maxDate={new Date()}
                      isEditableProps={isEditable}
                      // fullWidth={true}
                    />
                  </div>
                </div>
                <div className={classes.innerDivStyle}>
                  English :
                  <div className={classes.justifyCenterStyle}>
                    <label htmlFor="englishSpeak">Speak : </label>
                    <CheckboxField
                      name={"englishSpeak"}
                      isEditableProps={isEditable}
                    />
                  </div>
                  <div className={classes.justifyCenterStyle}>
                    <label htmlFor="englishRead">Read : </label>
                    <CheckboxField
                      name={"englishRead"}
                      isEditableProps={isEditable}
                    />
                  </div>
                  <div className={classes.justifyCenterStyle}>
                    <label htmlFor="englishWrite">Write : </label>
                    <CheckboxField
                      name={"englishWrite"}
                      isEditableProps={isEditable}
                    />
                  </div>
                </div>
                <div className={classes.innerDivStyle}>
                  <label htmlFor="subscription">Subscription : </label>
                  {isEditable ? (
                    <RadioButtonsGroup
                      name={"subscription"}
                      data={subscriptionStatusOptions}
                    />
                  ) : formikProps.values.subscription === true ? (
                    <label htmlFor="subscription">Active</label>
                  ) : (
                    <label htmlFor="subscription">Inactive</label>
                  )}
                </div>
                <div>
                  {assetdataTemp.map((key, index) => {
                    return (
                      <div>
                        <div className={classes.innerDivStyle}>
                          Asset Name :
                          {isEditable ? (
                            <TextFieldComponent
                              defaultProps={{
                                name: `assetDetails[${index}]assetName`,
                                // label: "Name",
                                fullWidth: false,
                                // placeholder: "Enter name",
                              }}
                            />
                          ) : (
                            <label htmlFor="firstName">{key.assetName}</label>
                          )}
                        </div>
                        <div className={classes.innerDivStyle}>
                          Asset Id :
                          {isEditable ? (
                            <TextFieldComponent
                              defaultProps={{
                                name: `assetDetails[${index}]assetId`,
                                // label: "Name",
                                fullWidth: false,
                                // placeholder: "Enter name",
                              }}
                            />
                          ) : (
                            <label htmlFor="firstName">{key.assetId}</label>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  <button
                    className="button add"
                    type="button"
                    onClick={() => addFormFields()}
                  >
                    Add
                  </button>
                </div>
                <div>
                  {isEditable ? (
                    <Button
                      type="submit"
                      variant="contained"
                      color="primary"
                      disabled={formikProps.isSubmitting}
                      className={classes.buttonContainer}
                    >
                      Save
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      variant="contained"
                      color="secondary"
                      className={classes.buttonContainer}
                    >
                      Edit
                    </Button>
                  )}
                </div>
              </div>
            </Form>
          )}
        </Formik>
      </div>
    </div>
  );
};

export default BasicForm;
